import os
import subprocess
import threading
import uuid
import json
from datetime import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Project
from .serializers import ProjectSerializer
from config.models import Config


def stream_process(cmd, cwd, log_file_path, channel_group):
    """
    在后台执行命令，将输出写入文件并通过频道推送日志消息。
    """
    channel_layer = get_channel_layer()
    with open(log_file_path, 'a', encoding='utf-8') as log_f:
        process = subprocess.Popen(
            cmd, cwd=cwd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True
        )
        for line in process.stdout:
            log_f.write(line)
            async_to_sync(channel_layer.group_send)(
                channel_group,
                {"type": "log.message", "message": line}
            )
        process.wait()
    # 发送完成消息
    async_to_sync(channel_layer.group_send)(
        channel_group,
        {"type": "log.complete", "timestamp": datetime.utcnow().isoformat()}
    )


class ProjectViewSet(viewsets.ModelViewSet):
    """
    提供项目 CRUD 及 clone/update/switch-branch/build/deploy/bulk 操作，
    并支持日志持久化与实时推送。
    """
    queryset = Project.objects.all().order_by('-created_at')
    serializer_class = ProjectSerializer

    @action(detail=True, methods=['post'], url_path='clone')
    def clone_project(self, request, pk=None):
        project = self.get_object()
        cfg = Config.objects.first()
        root = cfg.projects_root
        local_path = os.path.join(root, project.title)
        os.makedirs(local_path, exist_ok=True)
        task_id = str(uuid.uuid4())
        log_dir = cfg.log_directory
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{task_id}.log")
        channel_group = f"logs_{task_id}"
        # 异步执行克隆
        cmd = f"git clone {project.git_url} ."
        threading.Thread(
            target=stream_process,
            args=(cmd, local_path, log_file, channel_group),
            daemon=True
        ).start()
        project.local_path = local_path
        project.current_branch = project.default_branch
        project.status = 'UpToDate'
        project.save()
        return Response({'task_id': task_id})

    @action(detail=True, methods=['post'], url_path='update')
    def update_project(self, request, pk=None):
        project = self.get_object()
        path = project.local_path
        if not path or not os.path.isdir(path):
            return Response({'detail': 'Project not cloned locally'}, status=status.HTTP_400_BAD_REQUEST)
        cfg = Config.objects.first()
        task_id = str(uuid.uuid4())
        log_dir = cfg.log_directory
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{task_id}.log")
        channel_group = f"logs_{task_id}"
        cmd = "git fetch && git pull"
        threading.Thread(
            target=stream_process,
            args=(cmd, path, log_file, channel_group),
            daemon=True
        ).start()
        project.status = 'UpToDate'
        project.save()
        return Response({'task_id': task_id})

    @action(detail=True, methods=['patch'], url_path='switch-branch')
    def switch_branch(self, request, pk=None):
        project = self.get_object()
        branch = request.data.get('branch')
        if not branch:
            return Response({'detail': 'branch required'}, status=status.HTTP_400_BAD_REQUEST)
        path = project.local_path
        if not path or not os.path.isdir(path):
            return Response({'detail': 'Project not cloned locally'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            subprocess.check_call(['git', 'fetch'], cwd=path)
            subprocess.check_call(['git', 'checkout', branch], cwd=path)
        except subprocess.CalledProcessError as e:
            return Response({'detail': f'Git error: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        project.current_branch = branch
        project.save()
        return Response({'status': 'branch switched'})

    @action(detail=True, methods=['post'], url_path='build')
    def build_project(self, request, pk=None):
        project = self.get_object()
        path = project.local_path
        if not path or not os.path.isdir(path):
            return Response({'detail': 'Project not cloned locally'}, status=status.HTTP_400_BAD_REQUEST)
        cfg = Config.objects.first()
        script = project.build_script or cfg.default_build_script
        task_id = str(uuid.uuid4())
        log_dir = cfg.log_directory
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{task_id}.log")
        channel_group = f"logs_{task_id}"
        threading.Thread(
            target=stream_process,
            args=(script, path, log_file, channel_group),
            daemon=True
        ).start()
        return Response({'task_id': task_id})

    @action(detail=True, methods=['post'], url_path='deploy')
    def deploy_project(self, request, pk=None):
        project = self.get_object()
        env = request.data.get('env')
        cfg = Config.objects.first()
        group = cfg.rsync_groups.get(env)
        if not group:
            return Response({'detail': 'Invalid env'}, status=status.HTTP_400_BAD_REQUEST)
        src = os.path.join(cfg.output_root, project.code, project.title)
        dest = f"{group['host']}:{group['path']}"
        rsync = group['rsync']
        task_id = str(uuid.uuid4())
        log_dir = cfg.log_directory
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{task_id}.log")
        channel_group = f"logs_{task_id}"
        cmd = f"{rsync} -avz {src} {dest}"
        threading.Thread(
            target=stream_process,
            args=(cmd, cfg.output_root, log_file, channel_group),
            daemon=True
        ).start()
        return Response({'task_id': task_id})

    @action(detail=False, methods=['post'], url_path='bulk/build')
    def bulk_build(self, request):
        ids = request.data.get('ids', [])
        results = {}
        for pk in ids:
            resp = self.build_project(request, pk)
            results[pk] = resp.data
        return Response(results)

    @action(detail=False, methods=['post'], url_path='bulk/deploy')
    def bulk_deploy(self, request):
        ids = request.data.get('ids', [])
        env = request.data.get('env')
        results = {}
        for pk in ids:
            sub_req = request._request
            sub_req._full_data = {'env': env}
            resp = self.deploy_project(sub_req, pk)
            results[pk] = resp.data
        return Response(results)
    
    @action(detail=True, methods=['post'], url_path='open')
    def open(self, request):
        project = self.get_object()
        cfg = Config.objects.first()
        local_dir = os.path.join(cfg.projects_root, project.code, project.title)
        if os.path.exists(os.path.join(local_dir, ".creator")):
            # creator project
            # load package.json
            package_json_path = os.path.join(local_dir, "package.json")
            if not os.path.isfile(package_json_path):
                return Response({msg: "package.json not found"}, 2)
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_json = json.load(f)
            if package_json and package_json.creator:
                if cfg.editor_paths and cfg.editor_paths.creator:
                    target = list(filter(lambda x: x.version == package_json.creator.version, cfg.editor_paths.creator))
                    if not target:
                        return Response({msg: "no engine found"})
                    subprocess.Popen([target.path, local_dir])
                    return Response({msg: "success"})
                return Response({msg: "no engine found"})
            return Response({msg: "not a valid cocos creaor project"})
        else:
            # this is a egret project
            if cfg.editor_paths.egret:
                subprocess.Popen([cfg.editor_paths.egret.path, local_dir])
                return Response({msg: "success"})
            return Response({msg: "no engine found"})
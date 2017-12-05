import os
import subprocess
import sys
from pprint import pprint

import docker
from flask import Flask, request


REPOS = {
    'someorg/somerepo': {
        'deploy': {
            'source': '/data/{site_name}',
            'target': '/data/{site_name}.build',
        },
        'master': {
            'source': '/data/preview.{site_name}',
            'target': '/data/preview.{site_name}.build',
        },
    },
}

app = Flask(__name__)


@app.route("/", methods=['get', 'post'])
def main():
    data = request.json
    repo = data.get('repository', {}).get('full_name', '')
    branch = data.get('ref', '').replace('refs/heads/', '')
    branch_config = REPOS.get(repo)
    if branch_config and branch in branch_config:
        res = build(branch, **branch_config[branch])
        if res:
            pprint(
                {
                    'repo': repo,
                    'branch': branch,
                    'head_commit': data['head_commit'],
                    'pusher': data['pusher'],
                    'build_result': res.split(b'\n')
                },
                stream=sys.stderr
            )

        else:
            print("Error building", file=sys.stderr)
    return "OK"


def build(branch, source, target, **kw):
    os.chdir(source)
    subprocess.check_output(["git", "fetch", "--all"])
    subprocess.check_output(["git", "reset", "--hard", f"origin/{branch}"])
    client = docker.from_env()
    out = client.containers.run(
        'jekyll/minimal',
        ['-c', 'gem install jekyll-seo-tag && cd /in && jekyll build -d /out'],
        entrypoint=["/bin/sh"],
        volumes={
            source: {
                'bind': '/in', 'mode': 'rw'
            },
            target: {
                'bind': '/out', 'mode': 'rw'
            },
        },
        remove=True,
        detach=False,
        stderr=True,
        stdout=True,
    )
    return out

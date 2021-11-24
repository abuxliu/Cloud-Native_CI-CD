import json
import os
import datetime
from flask import Flask, request
from git import Repo
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(2)
app = Flask(__name__)


def git_checkout(ci_info):
    Repo.clone_from(ci_info['git_http_url'], ci_info['name'])
    repo = Repo(ci_info['name'])
    repo.git.checkout(ci_info['tag'])


def docker_build_and_push(ci_info):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    path = cur_dir + '/' + ci_info['name']
    repository = 'abuxliu/' + ci_info['name']
    tag = ci_info['tag']
    os.system('docker login --username=abuxliu@gmail.com --password=***')
    cmd = 'docker build ' + path + ' -t ' + repository + ':' + tag
    os.system(cmd)
    os.system('docker push ' + repository + ':' + tag)
    os.system('/usr/bin/rm -rf demo')


def continuous_integration(ci_info):
    start_time = datetime.datetime.now()

    git_checkout(ci_info)
    docker_build_and_push(ci_info)

    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    print("CI Run Time: " + str(run_time))


def continuous_delivery(cd_info):
    start_time = datetime.datetime.now()

    cmd = '/usr/local/bin/helm upgrade --install {} charts/{} --set image.tag={}'
    cmd = cmd.format(cd_info['name'], cd_info['name'], cd_info['tag'])
    os.system(cmd)
    os.system('echo Yes')

    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    os.system('echo CD_Run_Time:' + str(run_time))


@app.route('/api/code', methods=['POST'])
def api_code():
    start_time = datetime.datetime.now()

    event = request.headers.get("X-Gitlab-Event")
    if event == 'Tag Push Hook':
        body = request.data
        body = str(body, "utf-8")
        body = json.loads(body)
        commit_id = body['checkout_sha']
        ref = body['ref']
        tag = str(ref).split('/')[-1]
        user_username = body['user_username']
        name = body['project']['name']
        git_http_url = body['project']['git_http_url']
        result = {'commit_id': commit_id,
                  'user_username': user_username,
                  'name': name,
                  'git_http_url': git_http_url,
                  'tag': tag}
        executor.submit(continuous_integration, result)
    else:
        result = {'event': event}

    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    print("API Code Run Time: " + str(run_time))

    return json.dumps(result, ensure_ascii=False)


@app.route('/api/image', methods=['POST'])
def api_image():
    start_time = datetime.datetime.now()

    body = request.data
    body = str(body, "utf-8")
    body = json.loads(body)
    tag = body['push_data']['tag']
    name = body['repository']['name']
    namespace = body['repository']['namespace']
    region = body['repository']['region']
    result = {'repository': 'registry.' + region + '.aliyuncs.com/' + namespace + '/' + name, 'name': name, 'tag': tag}
    executor.submit(continuous_delivery, result)

    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    print("API Image Run Time: " + str(run_time))

    return json.dumps(result, ensure_ascii=False)


if __name__ == '__main__':
    app.run(port=50080, host='0.0.0.0', debug=True)

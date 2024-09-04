import os
import shutil
import subprocess
import typer

app = typer.Typer()

def create_tmp_directory():
    os.makedirs('./tmp', exist_ok=True)

def copy_files():
    for file in os.listdir('../'):
        if file.endswith('.py') or file == '.env':
            shutil.copy(os.path.join('../', file), './tmp')

def export_requirements():
    subprocess.run(['poetry', 'export', '-f', 'requirements.txt', '--output', './tmp/requirements.txt', '--without-hashes'], check=True)

@app.command()
def build_data_pipeline():
    subprocess.run(['docker', 'build', '--platform', 'linux/amd64', '-t', 'jwilliams-stockpicker-datapipeline', '-f', 'Dockerfile', '.'], check=True)

@app.command()
def run_data_pipeline():
    subprocess.run(['docker', 'run', '--hostname', 'jwilliams-stockpicker-datapipeline', '-it', 'jwilliams-stockpicker-datapipeline'], check=True)

@app.command()
def run_s3_listener():
    subprocess.run(['docker', 'run', '--hostname', 'jwilliams-stockpicker-s3-listener', '-it', 'jwilliams-stockpicker-s3-listener'], check=True)

@app.command()
def build_s3_listener():
    subprocess.run(['docker', 'build', '--platform', 'linux/amd64', '-t', 'jwilliams-stockpicker-s3-listener', '-f', 'Dockerfile_S3', '.'], check=True)

@app.command()
def deploy_to_fargate():
    try:
        subprocess.run(
            ["aws", "ecr", "get-login-password", "--region", "us-east-2"],
            check=True,
            stdout=subprocess.PIPE
        ).stdout.decode('utf-8')

        subprocess.run(
            ["docker", "login", "--username", "AWS", "--password-stdin", "461485115270.dkr.ecr.us-east-2.amazonaws.com"],
            input=subprocess.run(
                ["aws", "ecr", "get-login-password", "--region", "us-east-2"],
                check=True,
                stdout=subprocess.PIPE
            ).stdout,
            check=True
        )

        subprocess.run(
            ["docker", "tag", "jwilliams-stockpicker-datapipeline:latest", "461485115270.dkr.ecr.us-east-2.amazonaws.com/jwilliams-stockpicker-datapipeline:latest"],
            check=True
        )

        subprocess.run(
            ["docker", "push", "461485115270.dkr.ecr.us-east-2.amazonaws.com/jwilliams-stockpicker-datapipeline:latest"],
            check=True
        )

        script_dir = os.path.dirname(__file__)
        relative_path = "fargate-task-definition.json"
        absolute_path = os.path.abspath(os.path.join(script_dir, relative_path))
        print(absolute_path)
        subprocess.Popen(
            ["aws", "ecs", "register-task-definition", "--cli-input-json", f"fileb://{absolute_path}"]
        )

        subprocess.Popen(
            [
                "aws", "ecs", "run-task",
                "--cluster", "jwilliams-ecs-dev",
                "--launch-type", "FARGATE",
                "--task-definition", "jwilliams-stockpicker-datapipeline-def",
                "--network-configuration", "awsvpcConfiguration={subnets=[subnet-49862104,subnet-e7f4a58e,subnet-30dc414b],securityGroups=[sg-2a2dc242],assignPublicIp=ENABLED}"
            ]
        )
        return
    except subprocess.CalledProcessError as e:
        print(f"Error during fargate deploy: {e}")
        return

if __name__ == "__main__":
    create_tmp_directory()
    copy_files()
    export_requirements()
    app()
    shutil.rmtree('./tmp')
import os
import json
import git
import textwrap
import openai
from github import Github

TOKEN_LIMIT = 4096  # OpenAI's token limit for API calls

def get_file_content(file_path):
    """ Reads the content of a file. """
    with open(file_path, 'r') as file:
        return file.read()

def get_changed_files(pr):
    """ Fetches changed files in a pull request. """
    repo = git.Repo.clone_from(pr.base.repo.clone_url, to_path='./repo', branch=pr.head.ref)
    base_ref = f"origin/{pr.base.ref}"
    head_ref = f"origin/{pr.head.ref}"
    diffs = repo.git.diff(base_ref, head_ref, name_only=True).split('\n')

    files = {}
    for file_path in diffs:
        try:
            files[file_path] = get_file_content('./repo/' + file_path)
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")
    
    return files

def send_to_openai(files):
    """ Sends changed files to OpenAI for review. """
    code = '\n'.join(files.values())
    chunks = textwrap.wrap(code, TOKEN_LIMIT)

    reviews = []
    for chunk in chunks:
        message = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Review the following code:\n{chunk}"}],
        )
        reviews.append(message['choices'][0]['message']['content'])
    
    return "\n".join(reviews)

def post_comment(pr, comment):
    """ Posts a comment on the pull request. """
    pr.create_issue_comment(comment)

def main():
    """ Orchestrates the code review process. """
    with open(os.getenv('GITHUB_EVENT_PATH')) as json_file:
        event = json.load(json_file)

    pr = Github(os.getenv('GITHUB_TOKEN')).get_repo(event['repository']['full_name']).get_pull(event['number'])
    
    files = get_changed_files(pr)
    review = send_to_openai(files)
    post_comment(pr, review)

if __name__ == "__main__":
    main()

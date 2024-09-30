from flask import Flask, request, jsonify, render_template
import anthropic
import json
import requests
from requests.auth import HTTPBasicAuth
import re
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()

claude_api_key = os.getenv("CLAUDE_API_KEY")
jira_api_token = os.getenv("JIRA_API_TOKEN")
jira_user = os.getenv("JIRA_USER")
client = anthropic.Anthropic(api_key=claude_api_key)
claude_model = "claude-3-5-sonnet-20240620"

system_prompt = """
You are an assistant that is part of a team of software developers.
You'll be given a bulk of information and you need to extract the relevant information to create a Jira issue describing it.
You need to reply on a JSON format including 2 keys: 'title' (string) and 'description' (string).
'title' should be a short description of the task.
'description' should contain clear information about the all the context you can gather about that task. Feel free to include links and lists here. Make is as short as possible.
"""

jira_url = "https://ridecircuit.atlassian.net/rest/api/2/issue"
jira_auth = HTTPBasicAuth(jira_user, jira_api_token)
jira_headers = {
  "Accept": "application/json",
  "Content-Type": "application/json"
}

def process_issue(issue_text, project_id, issue_id):
    
    message = client.messages.create(
        model=claude_model,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": issue_text}
        ],
    )

    jissue_dict = {
        "title": "[JISSUE]",
        "description": ""
    }
    
    json_string = message.content[0].text

    try:
        escaped_string = re.sub(r'[\x00-\x1f\x7f-\x9f]', '\n', json_string)
        json_object = json.loads(escaped_string)
        jissue_dict['title'] = jissue_dict['title'] + " " + json_object['title']
        jissue_dict['description'] = json_object['description']
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        jissue_dict['description'] = json_string

    payload = json.dumps({
            "fields": {
                "description": jissue_dict['description'],
                "project": {
                    "id": project_id
                },
                "issuetype": {
                    "id": issue_id
                },
                "summary": jissue_dict['title'],
            }
        })
    
    response = requests.request(
            "POST",
            jira_url,
            data=payload,
            headers=jira_headers,
            auth=jira_auth
        )
    
    return jsonify({"response": response.text}), 200


@app.route('/issue-mobile', methods=['POST'])
def issue_mobile():
    data = request.get_json()
    if 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    
    return process_issue(data['text'], "10012", "10002")
    
@app.route('/issue-backend', methods=['POST'])
def issue_backend():
    data = request.get_json()
    if 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    
    return process_issue(data['text'], "10013", "10002")

@app.route('/issue-infra', methods=['POST'])
def issue_infra():
    data = request.get_json()
    if 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    
    return process_issue(data['text'], "10014", "10002")

@app.route('/issue-test', methods=['POST'])
def issue_test():
    data = request.get_json()
    if 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    
    return process_issue(data['text'], "10002", "10008")

    
if __name__ == '__main__':
    app.run(debug=True)
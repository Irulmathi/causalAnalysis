from flask import Flask, request, jsonify
import os
from openai import AzureOpenAI
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
 
# Ensure these environment variables are set or replace with your values
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
 
print(AZURE_OPENAI_ENDPOINT,AZURE_OPENAI_KEY)
# Predefined categories and subcategories

predefined_categories = {

    "access related issues": ['login related', 'file access related', 'admin access request', 'license request', 'other'],
    "application related issues": ['SAP related', 'ms teams related', 'browser related', 'outlook related', 'jira related', 'Other'],
    "Hardware related issues": ['workstation', 'windows laptop', 'Mac laptop', 'asset request', 'other'],
    "Security related issues": ['phishing report', 'stolen report', 'other'],
    "Network issues": ['LAN issue', 'VPN connectivity issue', 'High speed network request'],
    "Other issues": ['HR related issues', 'Facility management issues', 'others']
    }
 
# Data structure to hold counts and incidents
incident_store = {category.lower(): {'count': 0,
                             'subcategories': {subcategory.lower(): {'count': 0, 'incidents': []} for subcategory in subcategories}
                            } for category, subcategories in predefined_categories.items()}
 
def complete_short_description(short_description):
    return "the short description is : " + short_description
 
def complete_time_taken(time_taken):
    time_taken = (time_taken // 60) if (time_taken > 0) else 0
    time_taken_prompt = 'The time taken for resolution in minutes is ' + str(time_taken)
    return time_taken_prompt
 
def complete_closure_method(closure_method):
    return "How the issue was solved: " + closure_method
 
def complete_description(description):
    return "Here is another detailed overview or a chat history between the support agent and user: " + description
 
def get_question():
    category = get_categories()
    question = f"""With the given context about an incident. 
    Give category and sub category of the incident above {category}.
    The response should have Category: ,Subcategory: , Root cause brief: , problem fix: ,detailed agent performance report: ,issue brief:"""
    return question
 
def get_categories():
    category ='''The categories and subcategories as a dictionary of key value pairs 
    {"access related issues":['login related','file access related','admin access request','license request','other'],
     "application related issues":['SAP related','ms teams related','browser related','outlook related','jira related','Other'],
      "Hardware related issues":['workstation','windows laptop', 'Mac laptop', 'asset request', 'other'],
       "Security related issues" :['phishing report', 'stolen report', 'other'], 
       "Network issues": ['LAN issue', 'VPN connectivity issue', 'High speed network request'],
        "Other issues":['HR related issues', 'Facility management issues', 'others']}'''
    return category
 
def get_prompt(data):
    short_description = data['short_description']
    short_description = complete_short_description(short_description)
    time_taken = int(data["time_taken"])
    time_taken_prompt = complete_time_taken(time_taken)
    closure_method = data['closure_method']
    closure_method = complete_closure_method(closure_method)
    solution_description = data['solution_description']
    solution_description = complete_closure_method(closure_method)
 
    description = data['description']
    description = complete_description(description)
    question = get_question()
 
    prompt = short_description + newline + description + newline + time_taken_prompt + newline + closure_method + newline + solution_description + question
 
    return prompt
 
def get_chain_prompt(data):
    prompt = "Find if there are any correlations between the events below. if you find any create a chain (give it to me in the following format root cause: , connected incidents: , how they are connected: , incident short brief: ). Just give a one line answer" + newline
    for item in data:
        incident_no = item["incident_no"]
        time = item["time"]   
        solution_description = item["solution_description"]
        description = item["description"]
        root_cause = item["root cause"]
        line = "incident_no: " + incident_no + comma + "time: " + time + comma + "solution description: " + solution_description + comma + "description or chat history: " + description + comma + "Root cause:" + root_cause + newline
        prompt += line
    return prompt
 
comma = ", "
newline = "\n"
 
def generate_llm_output(prompt):
    client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_KEY, api_version="2024-02-15-preview")
    response = client.chat.completions.create(model="GPT4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
 
    return response.choices[0].message.content
 
def update_incident_store(category, subcategory, incident_id):
    print(category, subcategory, incident_id)
    a = incident_store[category]['count']
    print(a)
    # Update the counts and add the incident ID
    incident_store[category]['count'] += 1
    b = category
    print(b)
    incident_store[category]['subcategories'][subcategory]['count'] += 1
    c= incident_id
    print(c)
    incident_store[category]['subcategories'][subcategory]['incidents'].append(incident_id)
    # print(f"Updated {category} - {subcategory}: {incident_store[category]['subcategories'][subcategory]['count']} incidents")
    # print(f"Total incidents in {category}: {incident_store[category]['count']}")
    # Print the entire store after updating

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    if not data:
        return jsonify({'error': 'No input data provided'}), 400
 
    try:
        prompt = get_prompt(data)
        llm_inference = generate_llm_output(prompt)
        data["llm_inference"] = llm_inference
 
        # Update incident store
        category = data.get('category')
        subcategory = data.get('subcategory')
        incident_id = data.get('incident_id')
        if category and subcategory.keys and incident_id:
            update_incident_store(category, subcategory, incident_id)
 
        return jsonify(data)
    except Exception as e:
        response = jsonify({"error": "unable to process request as necessary fields were not passed", "details": str(e)})
        return response
 
 
@app.route('/forlist', methods=['POST'])
def forlist():
    input_list = request.json
    output = []
    if not input_list:
        return jsonify({'error': 'No input data provided'}), 400
    try:
        for data in input_list:
            prompt = get_prompt(data)
            llm_inference = generate_llm_output(prompt)
            data["llm_inference"] = llm_inference
            output.append(data)
            print("llm_inference", llm_inference)
            llm_cat=llm_inference[(llm_inference.lower().find("category")+9):(llm_inference.lower().find("subcategory"))]
            # print("llm" ,llm_cat)
            llm_subcat=llm_inference[(llm_inference.lower().find("subcategory")+12):(llm_inference.lower().find("root cause"))]
            # print(llm_subcat)
            incident_no = data.get('incident_no')
            if llm_cat and llm_subcat and incident_no:
                # print("llm_cat",llm_cat )
                # print("llm_subcat",llm_subcat)
                # print("incident_no", incident_no)
                update_incident_store(llm_cat.lower().strip(), llm_subcat.lower().strip(), incident_no.strip())
 
        return jsonify(output)
    except Exception as e:
        response = jsonify({"error": "unable to process request", "details": str(e)})
        return response
 
 
@app.route('/getchain', methods=['POST'])
def getchain():
    data = request.json
    if not data:
        return jsonify({'error': 'No input data provided'}), 400
 
    try:
        prompt = get_chain_prompt(data)
        llm_inference = generate_llm_output(prompt)
        return jsonify({"llm_inference": llm_inference})
    except Exception as e:
        response = jsonify({"error": "unable to process request as necessary fields were not passed", "details": str(e)})
        return response
 
 
@app.route('/getoverview', methods=['GET'])
def get_overview():
    overview = []
    for category, details in incident_store.items():
        category_overview = {
            category: {
                'count': details['count'],
                'subcategories': {}
            }
        }
        for subcategory, subdetails in details['subcategories'].items():
            category_overview[category]['subcategories'][subcategory] = {
                'count': subdetails['count'],
                'incidents': subdetails['incidents']
            }
        overview.append(category_overview)
    return jsonify(overview)
 
 
if __name__ == '__main__':
    app.run(debug=True)

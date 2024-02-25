from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from kubernetes import client, config
import datetime
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
from pymongo import MongoClient
import json

# cors allow all
from fastapi.middleware.cors import CORSMiddleware

 # Load variables from .env file
load_dotenv() 

# validate that all the required environment variables are set
required_env_vars = [
    "AZURE_OPENAAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_VERSION",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "MODEL_NAME",
    "MAX_TOKENS",
    "MONGODB_URI",
    "SCAN_INTERVAL_SECONDS",
    "LIST_NAMESPACE"
]

for env_var in required_env_vars:
    if env_var not in os.environ:
        raise ValueError(f"Environment variable {env_var} is not set")

# configure the openai client
azure_endpoint = os.getenv("AZURE_OPENAAI_ENDPOINT")
azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_version = os.getenv("AZURE_OPENAI_VERSION")
azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
openai_client    = AzureOpenAI(
  azure_endpoint    = azure_endpoint,
  api_key           = azure_openai_key,
  api_version       = azure_openai_version


)

# print all required_env_vars values to the console
for env_var in required_env_vars:
    print(f"{env_var}: {os.getenv(env_var)}")

if os.getenv("ENVIRONMENT") == "dev":
    print("Running in dev environment")

    # configure the kubernetes client
    config.load_kube_config()
if os.getenv("ENVIRONMENT") == "incluster":
    print("Running in incluster environment")
    # configure the kubernetes client
    config.load_incluster_config()

# configure the mongodb client using user and password
mongodb_client = MongoClient(os.getenv("MONGODB_URI"))

# check if the database recommendations exists, if not create it
if "KubeAIWhisperer" in mongodb_client.list_database_names():
    print("Database KubeAIWhisperer exists")
else:
    print("Database KubeAIWhisperer does not exist, creating it")
    db = mongodb_client["KubeAIWhisperer"]
    # create a collection called recommendations
    collection = db["recommendations"]
    print("Collection recommendations has been created")

app = FastAPI()
# add cors middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PROMPT_TEMPLATE = """
    You are a professional DevOps engineer assistant, aiding the DevOps team in optimizing their Kubernetes cluster.

    Your role:
    - Analyze provided manifest files.
    - Offer recommendations aligned with industry best practices.

    {
    "Recommendations": [
        {
        "Deployment": "",
        "Namespace": "",
        "Title": "",
        "Category": "",
        "Severity": "",
        "Description": "",
        "Implementation": "<AN EXAMPLE OF THE YAML CODE, HOW TO IMPLEMENT THIS RECOMMENDATION, ENTER ONLY THE SPECIFIC PART OF THE CODE THAT IS RELEVANT TO THE RECOMMENDATION, NOT THE ENTIRE YAML>"
        }
    ],
    "IMPORTANT": [
        "Replay only the JSON object with the recommendations; do not include any other information.",
        "Do not include any explanations; only provide an RFC8259 compliant JSON response following this format without deviation.",
        "Do not include ```json in the beginning or end of the response.",
        "Do not include ``` in the end of the response.",
        "Provide at least 5 recommendations for each category (Security, Scalability, Reliability, Best Practices, Cost Optimization, Misconfiguration)."
    ]
    }
    """

# function to save the recommendations to the database
def save_recommendations_to_db(recommendations):
    # get the database
    db = mongodb_client["recommendations"]
    # create a collection called recommendations
    collection = db["recommendations"]
    
    data_to_insert = json.loads(recommendations.choices[0].message.content)

    # loop through the recommendations and insert them to the database
    for recommendation in data_to_insert["Recommendations"]:
        # add datetime to the recommendation
        recommendation["ScanTime"] = datetime.datetime.now()
        # insert the recommendations to the database
        collection.insert_one(recommendation)
    print("Recommendations have been saved to the database")

# function to analyze the resource
def analyze_resource(resource):
    message_text = [
        {
            "role": "system",
            "content": PROMPT_TEMPLATE
        },
        {
            "role": "user",
            "content": "Here the manifest file for the resource please provide recommendations: \n" + resource
        }
    ]
    completion = openai_client.chat.completions.create(
            model=os.getenv("MODEL_NAME"),
            messages = message_text,
            temperature=0.7,
            max_tokens=int(os.getenv("MAX_TOKENS")),
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
            )

    # save the recommendations to the database
    save_recommendations_to_db(completion)
    print("Recommendations have been saved to the database")

# health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# serve the index.html from the static folder
app.mount('/app', StaticFiles(directory='static', html=True), name='static')

# controller to get all the recommendations from the database
@app.get("/get-recommendations")
async def get_recommendations():
    try:
        # get the database
        db = mongodb_client["recommendations"]
        # create a collection called recommendations
        collection = db["recommendations"]
        # get all the recommendations from the database
        recommendations = list(collection.find())
        recommendations_list = []
        for recommendation in recommendations:
            # convert the ObjectId to string
            recommendation["_id"] = str(recommendation["_id"])
            recommendations_list.append(recommendation)
        return {"status": "ok", "recommendations": recommendations}, 200
    except Exception as e:
        print(f"Error: {e}")
        # return error message with status code 500
        return {"status": "error", "message": str(e)}, 500


# dlete all the recommendations from the database
@app.get("/delete-recommendations")
async def delete_recommendations():
    try:
        # get the database
        db = mongodb_client["recommendations"]
        # create a collection called recommendations
        collection = db["recommendations"]
        # delete all the recommendations from the database
        collection.delete_many({})
        return {"status": "ok", "message": "All recommendations have been deleted"}, 200
    except Exception as e:
        print(f"Error: {e}")
        # return error message with status code 500
        return {"status": "error", "message": str(e)}, 500

# watch deployment and write to file when changed
@app.get("/watch-deployment")
async def watch_deployment():

    try:
        deployments_scanned = 0

        print("Watching deployment")
        # Create an instance of the CoreV1Api class
        v1 = client.AppsV1Api()

        for namespace in os.getenv("LIST_NAMESPACE").split(","):            
            ret = v1.list_namespaced_deployment(namespace=namespace, watch=False).to_dict()
            for i in ret['items']:
                last_update = str(i['metadata']['creation_timestamp'])
                last_update = datetime.datetime.strptime(last_update, '%Y-%m-%d %H:%M:%S%z')
                now = datetime.datetime.now(datetime.timezone.utc)
                diff = now - last_update
                if diff.seconds < int(os.getenv("SCAN_INTERVAL_SECONDS")):
                    analyze_resource(str(i))
                    print(f"Deployment {i['metadata']['name']} has been created in the last 5 minutes")
                    deployments_scanned += 1
                else:
                    print(f"Deployment {i['metadata']['name']} has not been created in the last 5 minutes")

            return {
                "status": "ok",
                "message": f"{deployments_scanned} Deployments has been scanned"
                }, 200
    except Exception as e:
        print(f"Error: {e}")
        # return error message with status code 500
        return {"status": "error", "message": str(e)}, 500


# list all events from the namespace
@app.get("/list-events")
async def list_events():
    try:
        # Create an instance of the CoreV1Api class
        v1 = client.CoreV1Api()
        
        events = []
        # get all the events from the namespace
        ret = v1.list_namespaced_event(namespace="default", watch=False).to_dict()

        for event in ret['items']:
            # if the event type is Normal, remove it from the list
            if event['type'] != "Normal":
                events.append(event)
        return {"status": "ok", "events": events}, 200
    except Exception as e:
        print(f"Error: {e}")
        # return error message with status code 500
        return {"status": "error", "message": str(e)}, 500


# start the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
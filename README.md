# Instructions to set up project locally

## Copy the repo

- git clone https://github.com/demurphyh/MyFunctionProject.git

- cd MyFunctionProject

- VScode extensions: Azure Functions, Azurite

## Create virtual environment

- Mac: python -m venv myfirstproject
  - source myfirstproject/bin/activate
- Windows: python -m venv myfirstproject
  - myfirstproject\Scripts\activate

## Download requirements

- pip install -r requirements.txt

## Create file for app settings and connection srings

- Create local.settings.json

- Example
 {
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "COSMOS_STRING": "<cosmos-connection-string>,
    "DATABASE_NAME": "<database-name>",
    "CONTAINER_STRING": "<container-name>"
  }
}

## Running local function

- Start Azurite: Press F1 and search for Azurite: Start

- Start Function: Press F5 to run and debug

- Click the Azure icon in the Activity bar

- In the Workspace area, expand Local Project > Functions

- Right-click (Windows) or Ctrl-click (macOS) on TextAnalysis

- Select Execute Function Now...

- In the Enter request body prompt enter: { "text": "Serverless computing is amazing. It scales automatically." }

- Press Enter to send the request

- A notification will appear with the function's response.

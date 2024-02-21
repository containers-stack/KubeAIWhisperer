<img src="https://github.com/containers-stack/KubeAIWhisperer/blob/main/static/logo.png?raw=true" width="400">

# KubeAIWhisperer

Welcome to KubeAIWhisperer, your ultimate Kubernetes deployment monitoring tool empowered by AzureOpenAI.

## Overview

KubeAIWhisperer is designed to provide real-time insights and recommendations for optimizing your Kubernetes deployments. It leverages the latest advancements in AI to analyze your clusters and offer suggestions on security configurations, scaling strategies, and cost management. With KubeAIWhisperer, you can ensure your Kubernetes infrastructure is always performing at its best while minimizing risks and costs.

<img src="https://github.com/containers-stack/KubeAIWhisperer/blob/main/static/Screenshot.png" width="400" >

## Features

- **Automatic Monitoring**: KubeAIWhisperer continuously monitors your Kubernetes deployments, detecting any changes or new deployments instantly.

- **AI-driven Recommendations**: Powered by AzureOpenAI, KubeAIWhisperer offers actionable insights and best practices for security, scalability, and cost optimization.

- **Customizable Alerts**: Set up alerts based on specific criteria to stay informed about critical changes in your Kubernetes environment.

## Getting Started

### Prerequisites

- Kubernetes cluster up and running.
- Access to Kubernetes API server.
- Python 3.x installed.
- AzureOpenAI API key (Sign up [here](https://azure.microsoft.com/en-us/products/ai-services/openai-service) if you don't have one).

### Deployment
To deploy KubeAIWhisperer, follow these steps:

1. Update the deployment.yaml file with the necessary values under the configmap section. Ensure to replace placeholders with actual values:
   ```yaml
      apiVersion: v1
      kind: ConfigMap
      metadata:
      name: kubeaiwhisperer-config
      data:
      # AzureOpenAI endpoint URL
      AZURE_OPENAI_ENDPOINT: ""  
      # AzureOpenAI API key
      AZURE_OPENAI_API_KEY: ""
      # AzureOpenAI version
      AZURE_OPENAI_VERSION: ""
      # AzureOpenAI deployment name
      AZURE_OPENAI_DEPLOYMENT_NAME: ""
      # Name of the model to be used
      MODEL_NAME: ""
      # Maximum tokens to generate
      MAX_TOKENS: ""
      # MongoDB connection URI
      MONGODB_URI: ""
      # Interval in seconds to scan for changes
      SCAN_INTERVAL_SECONDS: ""
      # Namespaces to list for monitoring
      LIST_NAMESPACE: ""
      # Environment type (incluster or external)
      ENVIRONMENT: ""

2. Install the deployment using:
   ```bash
   kubectl apply -f deployment.yaml
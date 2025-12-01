# Kestra Demo Project

In this section, we'll set up Kestra on our local machines, connect it to GCP, run some Python and Java code. Additionally, we will set up a sync between GitHub and Kestra and use Subflows to make our flows more modular.

## Prerequisites

This demo project assumes you have Docker or a similarly compatible container or a Virtual Machine environment installed and running.

## How to install Kestra locally

In order to install Kestra locally, we need to do the following steps:

1. Install Minikube
1. Install Kubernetes tools (`kubectl`)
1. Start Minikube
1. Install the Helm CLI
1. Add Kestra Helm repo and install it
1. Wait for all pods to be healthy
1. Access Kestra UI

If you have already set some of those things up, feel free to skip.

> [!NOTE]
> The following documentation uses Helm (v3.19.0), Minikube (v1.37.0), and Kestra (1.0.8).

### Install Minikube

Minikube serves as an easy local setup for Kubernetes (k8s). 

Follow the steps in the [official installation guide](https://minikube.sigs.k8s.io/docs/start/) for your operating system, architecture and installer type.

### Install Kubernetes tools (kubectl)
(This actually got installed with Minikube for me -Andreas)

Access the [official docs](https://kubernetes.io/docs/tasks/tools/) to get the most up to date setup steps for your operating system.

> [!NOTE]
> The docs recommend running `kubectl cluster-info` to verify a proper configuration. But since we haven't started Minikube yet, this won't work so far.

### Start Minikube

This step simply requires the following command:

`minikube start`

Wait for the cluster to start.

You can validate that the setup was successful by running this command:

`kubectl get nodes`

or alternatively (as described in the Kubernetes tools docs):

`kubectl cluster-info`

### Install the Helm CLI

`Helm` is the package manager for Kubernetes. It is needed to install Kestra.

Follow the instructions in [the official docs](https://helm.sh/docs/intro/install/) for your operating system.

### Add Kestra Helm repo and install it

In order to add the Kestra helm repository, run the following command:

`helm repo add kestra https://helm.kestra.io/`

The installation, however, cannot be started yet. You first need to create a configuration.

Create a directory for your demo project (e.g. `/kestra`) and create a single file `config.yml` (the name does not matter, in Kestra you also often see `values.yaml`).

Add the following code to the file:

```yml
configurations:
  application:
    kestra:
      repository:
        type: h2
      storage:
        type: local
        local:
          basePath: /tmp/kestra/storage
      queue:
        type: h2
```

This will set the Kestra server URL to `localhost` on the port `8080`.

Create a quick dummy variable for GCP otherwise Kestra will not start (think we don't need that actually. I used the large config file. That was the problem)
``` bash
kubectl create secret generic gcp-credentials --from-literal=dummy="{}"
kubectl create secret generic kestra-secrets --from-literal=dummy="{}"

```

Then navigate to the aforementioned directory in the command line and run:

  ``` bash
  helm install kestra kestra/kestra -f config_simple.yml
  ```

The output should look similar to this:

![Screenshot of the example output of the step to install Kestra](/images/kestra-starting.png)

> [!NOTE]
> According to the docs of Kestra providing a config.yml file is not necessary. Nevertheless, in our own tests, this caused errors why the aforementioned config is needed.

### Wait for all pods to be healthy

Use the following command to watch for changes on the pods:

  ``` bash
  kubectl get pods -l app.kubernetes.io/name=kestra -w
  ```

Wait until 2/2 containers have started (see below):

![Screenshot of the example output when Kesta has started.](/images/kestra-started.png)

Lastly, you need to forward the port from the pod to your local machine via:

  ``` bash
  kubectl port-forward svc/kestra 8080:8080
  ```

UPDATE:
Just do this command and keep the cli open:

  ``` bash
  minikube service kestra
  ```

### Access Kestra UI

Use the IP and Port that minikube service kestra shows

![Started Kestra UI](/images/kestra-ui.png)

## Connect Kestra to GCP

### GCP Account & Project Setup

If you already have a GCP account and project skip ahead. If not, here's what you need:

1. Go to https://console.cloud.google.com/
1. Sign in with your Google account
1. Create a new project (e.g., "kestra-demo")

> [!NOTE]
> You need to provide a payment method in this step. 

> [!IMPORTANT]
> Be aware that queries against GCP can incur costs. Check twice before running queries. 

### Install GCP CLI MAC

If you have the GCP CLI already installed, you can skip this command.

On Mac:
```bash
curl https://sdk.cloud.google.com | bash

gcloud init
```

During `gcloud init`, it will:

- Ask you to log in with your Google account
- Ask you to select or create a project (use the actual name of the project - in our case 'kestra-demo').

### Install GCP CLI WSL2
```bash
sudo apt update && sudo apt install apt-transport-https ca-certificates gnupg

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo tee /usr/share/keyrings/cloud.google.gpg > /dev/null

sudo apt update && sudo apt install google-cloud-sdk


### Enable required APIs

For this tutorial, we will use Google Storage and BigQuery. Therefore, we need to enable their APIs.

```bash
gcloud services enable storage.googleapis.com

gcloud services enable bigquery.googleapis.com
```

### Create a GCS Bucket

> [!NOTE]
> Replace 'com-mycompany-kestra-demo' with something unique (bucket names are global).

```bash
gsutil mb -l europe-west3 gs://com-mycompany-kestra-demo/
```

Verify if it was created, via:
```bash
gsutil ls
```

> [!NOTE]
> Bucket names must be globally unique across all of GCP, so a reverse domain identifier with dashes combined with the project name makes sense (e.g. `gs://com-mycompany-kestra-demo`).

### Create a BigQuery Dataset (for testing)

For testing, we'll need a dataset. Run these commands to create and verify them:

```bash
bq mk --dataset --location=europe-west3 kestra_test

bq ls
```

The second command should print out the file.

### Create a service account

A service account is like a robot user or machine identity in GCP. It's used when applications (like Kestra) need to access GCP resources automatically, without a human logging in.

These are the required commands you need to run.

1. Create the service account

```bash
gcloud iam service-accounts create kestra-sa --display-name="Kestra Service Account"
```
2. Get and store your project ID 
```bash
PROJECT_ID=$(gcloud config get-value project)
```
3. Grant it permissions for BigQuery 
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:kestra-sa@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/bigquery.admin"
```
4. Grant it necessary permissions for Cloud Storage
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:kestra-sa@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/storage.admin"
```

> [!IMPORTANT]
> For production, these permissions are maybe too broad. Consider not using the `bigquery.admin` and `storage.admin` role. 

### Generate and Download the JSON Key

These keys are now needed to perform uploads for the service account.

Run these commands:

1. Create and download the key
```bash
gcloud iam service-accounts keys create ~/kestra-gcp-key.json --iam-account=kestra-sa@${PROJECT_ID}.iam.gserviceaccount.com
```
2. Verify the file exists
```bash
ls -lh ~/kestra-gcp-key.json
```

You should see the file listed in the terminal output.

> [!WARNING]
> This file is sensitive! Don't commit it to git or share it publicly.

### Create Kubernetes Secret

Now the secret must be known to Kubernetes. Run these commands:

1. Create the secret in Kubernetes
```bash
kubectl create secret generic gcp-credentials \
  --from-file=key.json=$HOME/kestra-gcp-key.json
```
2. Verify it was created
```bash
kubectl get secrets
```

You should see the secret listed in the terminal output.

### Update Your Kestra Configuration

Update your `config.yml` file:

```yaml
configurations:
  application:
    kestra:
      repository:
        type: h2
      storage:
        type: gcs
        gcs:
          bucket: com-mycompany-kestra-demo # Use YOUR bucket name
          projectId: kestra-demo # Use YOUR project ID
      queue:
        type: h2
common:
  extraVolumes:
    - name: gcp-credentials
      secret:
        secretName: gcp-credentials
  extraVolumeMounts:
    - name: gcp-credentials
      mountPath: /gcp
      readOnly: true
  extraEnv:
    - name: GOOGLE_APPLICATION_CREDENTIALS
      value: /gcp/key.json
```

### Upgrade Kestra

```bashh
--> Don't use this one --> helm upgrade kestra kestra/kestra -f config.yml
helm upgrade --install kestra ./my-kestra

kubectl get pods -l app.kubernetes.io/name=kestra -w
```

Wait for it to show `2/2 Running` again (might take 1-2 minutes).

⚠️ In our tests, an upgrade did often not work. In this case run the following commands:

```bash
helm uninstall kestra

helm install kestra kestra/kestra -f config.yml

kubectl port-forward svc/kestra 8080:8080
```

### Verify GCP Connection

```bash
kubectl logs -l app.kubernetes.io/name=kestra -c kestra-standalone --tail=100 | grep -i "gcs\|gcp\|storage"
```

If you don't see any errors about GCS, you're good!

### Test the Connection With a Simple Flow

Go back to http://localhost:8080. If you haven't before, create a Kestra account in the UI and sign in. You might have to answer a few questions.

Your browser window should similar like this:
![UI when signed in to Kestra](/images/kestra-signed-in.png)

> [!IMPORTANT]
> Every time you uninstall and recreate Kestra, you also have to recreate your account.

#### Create Your First Flow

Select the option to create your first flow (e.g. 'Create my first flow'). You can skip all tutorials or watch them, whatever you prefer.

Completing or skipping the tutorial will lead you to this screen:

![Kestra Flows](/images/kestra-flows.png)

Now paste this flow which will create a simple text file with some text in it with Python:

```yaml
id: test-gcs-connection
namespace: dev.testing

tasks:
  - id: create_and_upload
    type: io.kestra.plugin.scripts.python.Script
    outputFiles:
      - "hello.txt"
    script: |
      with open('hello.txt', 'w') as f:
          f.write('Hello from Kestra! GCP connection works! 🎉')
  
  - id: upload_to_gcs
    type: io.kestra.plugin.gcp.gcs.Upload
    from: "{{ outputs.create_and_upload.outputFiles['hello.txt'] }}"
    to: "gs://com-mycompany-kestra-demo/test/hello.txt"
```
> [!IMPORTANT]
> Replace `com-mycompany-kestra-demo` with YOUR actual bucket name from earlier!

Click 'Save' and 'Execute'. 

After a successful run (indicated by green progress bars), run the following command (again replace with YOUR actual bucket name):

```bash
gsutil cat gs://com-mycompany-kestra-demo/test/hello.txt
```

This should output:
`Hello from Kestra! GCP connection works! 🎉`

## Run Code in Kestra

Kestra is very versatile and langauge-agnostic. It allows you to write your business logic with your preferred language and run it in a Docker container.

### Run Python Code in Kestra

In the previous section, we've already built a simple task that runs Python code in Kestra which basically uses a container through `io.kestra.plugin.scripts.python.Script`.

There are different ways to run Python code in Kestra. We will show two of them and how to exchange data between tasks.

👉 More info about [Python in Kestra](https://kestra.io/docs/how-to-guides/python).

#### Option 1: Simple Inline Python Script

As seen before, you can run Inline Python code in Kestra in the script property.

You can also specify output files and run code before running the script:

```yaml
id: python-data-processing
namespace: dev.testing

tasks:
  - id: process_data
    type: io.kestra.plugin.scripts.python.Script
    beforeCommands:
      - pip install pandas
    outputFiles:
      - "output.csv"
    script: |
      import pandas as pd
      
      # Create sample data
      data = {
          'name': ['Alice', 'Bob', 'Charlie'],
          'age': [25, 30, 35],
          'salary': [50000, 60000, 70000]
      }
      df = pd.DataFrame(data)
      
      # Transform: Calculate salary after 10% raise
      df['new_salary'] = df['salary'] * 1.1
      
      # Save output
      df.to_csv('output.csv', index=False)
      print(f"Processed {len(df)} records")
```

This script will do the following:

1. Install `Pandas` before the running commands.
1. Run a script that calculates the new salary after a 10% raise for each employer. 
1. Then write the dataframe into a CSV file `output.csv`.

You can access the ouput file through: `Outputs` > `process_data` (task ID) > `outputFiles` > `output.csv` (see image below).

![Generated output CSV file](/images/output-csv.png)

#### Option 2: Using Namespace Files

Inline Python scripts work for small code pieces and trying things out. For more serious tasks, it's prefered to maintain the Python code outside of the task and Flow.

You can accomplish this separation via Namespace files.

Here is how to do it:

1. In Kestra UI, go to your namespace (e.g. `dev.testing`) with: `Namespaces` > `dev` > `testing`.
1. Click on `Files`.
1. Create a file called `process_data.py` and paste the following code:
```python
import pandas as pd

def process_sales_data():
    # Create sample sales data
    data = {
        'product': ['Widget', 'Gadget', 'Doohickey'],
        'quantity': [100, 150, 200],
        'price': [10.0, 20.0, 15.0]
    }
    df = pd.DataFrame(data)
    
    # Calculate revenue
    df['revenue'] = df['quantity'] * df['price']
    
    # Save results
    df.to_csv('sales_report.csv', index=False)
    
    # Return summary
    total_revenue = df['revenue'].sum()
    return f"Total revenue: ${total_revenue:,.2f}"

if __name__ == "__main__":
    result = process_sales_data()
    print(result)
```

> [!NOTE]
> You can also create folder structures to improve maintainability and add a better structure.

4. Create a new flow that uses this namespace file:
```yaml
id: python-with-namespace-files
namespace: dev.testing

tasks:
  - id: run_script
    type: io.kestra.plugin.scripts.python.Commands
    namespaceFiles:
      enabled: true
    beforeCommands:
      - pip install pandas
    outputFiles:
      - "sales_report.csv"
    commands:
      - python process_data.py
```

### Exchange Data Between Tasks

The flows we looked at so far had a single tasks. However, you may want to chain multiple small modular tasks that run sequentially. That often requires to share data between these tasks.

Here is an example that shares data between two tasks:
```yaml
id: python-multi-step
namespace: dev.testing

tasks:
  - id: generate_data
    type: io.kestra.plugin.scripts.python.Script
    outputFiles:
      - "data.csv"
    script: |
      import csv
      
      # Generate data
      data = [
          ['name', 'score'],
          ['Alice', '85'],
          ['Bob', '92'],
          ['Charlie', '78']
      ]
      
      with open('data.csv', 'w', newline='') as f:
          writer = csv.writer(f)
          writer.writerows(data)
      
      print("Data generated successfully")
  
  - id: analyze_data
    type: io.kestra.plugin.scripts.python.Script
    beforeCommands:
      - pip install pandas
    inputFiles:
      data.csv: "{{ outputs.generate_data.outputFiles['data.csv'] }}"
    outputFiles:
      - "summary.txt"
    script: |
      import pandas as pd
      
      # Read the data from previous step
      df = pd.read_csv('data.csv')
      
      # Calculate statistics
      avg_score = df['score'].mean()
      max_score = df['score'].max()
      
      print(f"Average score: {avg_score:.2f}")
      print(f"Highest score: {max_score}")
      
      # Write summary
      with open('summary.txt', 'w') as f:
          f.write(f"Class Statistics\n")
          f.write(f"Average: {avg_score:.2f}\n")
          f.write(f"Maximum: {max_score}\n")
```

1. The task `generate_data` will generate a CSV-file `data.csv` with Python. 
1. The second task `analyze_data` will install Pandas to read from the previously generated CSV file (via `inputFiles` property) and find the average and maximum score.
1. Lastly, the second task will write the output into a `summary.txt` file.

The outputs will show both tasks and their respective `outputFiles`.

### Run Java Code in Kestra

Similar to Python, there are multiple ways available to run Java code.

#### Option 1: Simple Java (Compile & Run)

This flow compiles and runs Java directly in the container:

```yaml
id: java-hello-world
namespace: dev.testing

tasks:
  - id: run_java
    type: io.kestra.plugin.scripts.shell.Commands
    containerImage: eclipse-temurin:17-jdk
    commands:
      - |
        cat > HelloKestra.java << 'EOF'
        public class HelloKestra {
            public static void main(String[] args) {
                System.out.println("Hello from Java in Kestra!");
                System.out.println("Current time: " + java.time.LocalDateTime.now());
            }
        }
        EOF
      - javac HelloKestra.java
      - java HelloKestra
```

> [!IMPORTANT]
> Be aware that Java takes significantly longer than Python. So you may need to wait a few minutes. 

This easy way is using inline Java code which makes it not realistic for more than a quick testing. The code above will simply log 'Hello from Java in Kestra!' and the current time.

#### Option 2: Java with Namespace Files
Similar to Python, you can also create and maintain the Java code outside of the task and Flow with the help of Namespace files.

Here is how to do it:

1. In Kestra UI, go to your namespace (e.g. `dev.testing`) with: `Namespaces` > `dev` > `testing`.
1. Click on `Files`.
1. Create a file called `DataProcessor.java` and paste the following code:
```java
import java.io.*;
import java.util.*;

public class DataProcessor {
    public static void main(String[] args) throws IOException {
        // Read input
        List<String> names = Arrays.asList("Alice", "Bob", "Charlie", "Diana");
        
        // Process data
        System.out.println("Processing " + names.size() + " records...");
        
        // Write output
        try (PrintWriter writer = new PrintWriter("output.txt")) {
            for (String name : names) {
                writer.println(name.toUpperCase());
            }
        }
        
        System.out.println("✓ Processing complete!");
        System.out.println("Output saved to output.txt");
    }
}
```

> [!NOTE]
> Again, you can nest files in structures with folders to improve maintainability.

4. Create a new flow that uses this namespace file:
```yaml
id: java-with-namespace-files
namespace: dev.testing

tasks:
  - id: compile_and_run
    type: io.kestra.plugin.scripts.shell.Commands
    containerImage: eclipse-temurin:17-jdk
    namespaceFiles:
      enabled: true
    outputFiles:
      - "output.txt"
    commands:
      - javac DataProcessor.java
      - java DataProcessor
      - cat output.txt
```

This code will write one line for each name to a file `output.txt`. 

#### Option 3: Maven Project

This option is great for production-grade systems since it allows to specify dependencies easily and create reproducible builds along many other benefits.

Here is what you need:

1. Create a file `pom.xml` in your Namespace files (see Option 2 for how to do this).
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>kestra-demo</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>com.google.code.gson</groupId>
            <artifactId>gson</artifactId>
            <version>2.10.1</version>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.13.0</version>
            </plugin>
            <plugin>
                <groupId>org.codehaus.mojo</groupId>
                <artifactId>exec-maven-plugin</artifactId>
                <version>3.5.0</version>
                <configuration>
                    <mainClass>com.example.DataProcessor</mainClass>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```
2. Create a nested file `src/main/java/com/example/DataProcessor.java` (you don't have to create each folder manually, you can create folders by using `/` in the filename).
```java
package com.example;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import java.io.*;
import java.util.*;

public class DataProcessor {
    
    public static void main(String[] args) throws IOException {
        System.out.println("Starting Data Processor...");
        
        // Create sample data
        List<Person> people = Arrays.asList(
            new Person("Alice", 25, "Engineering"),
            new Person("Bob", 30, "Sales"),
            new Person("Charlie", 35, "Marketing")
        );
        
        // Process data using external library (Gson)
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        String json = gson.toJson(people);
        
        // Write output
        try (PrintWriter writer = new PrintWriter("output.json")) {
            writer.println(json);
        }
        
        // Generate summary
        double avgAge = people.stream()
            .mapToInt(Person::getAge)
            .average()
            .orElse(0);
        
        System.out.println("✓ Processed " + people.size() + " records");
        System.out.println("✓ Average age: " + String.format("%.1f", avgAge));
        System.out.println("✓ Output saved to output.json");
    }
    
    static class Person {
        private String name;
        private int age;
        private String department;
        
        public Person(String name, int age, String department) {
            this.name = name;
            this.age = age;
            this.department = department;
        }
        
        public int getAge() { return age; }
    }
}
```
3. Create a new flow that uses the code:
```yaml
id: java-maven-project
namespace: dev.testing

tasks:
  - id: build_and_run
    type: io.kestra.plugin.scripts.shell.Commands
    containerImage: maven:3.9-eclipse-temurin-17
    namespaceFiles:
      enabled: true
    outputFiles:
      - "output.json"
    commands:
      - ls -la  # Debug: see what files are available
      - mvn --version  # Show Maven version
      - mvn clean compile  # Compile the project
      - mvn exec:java  # Run the main class
      - cat output.json  # Show the output
```

The code in this example will show several logs and ultimately save a `output.json` file with three people (name, age, department).

## Synchronizing Code from GitHub

Kestra can automatically sync your code from Git repositories like GitHub, keeping your workflows and scripts version-controlled and up-to-date. This enables true GitOps workflows where Git becomes your single source of truth.

### Understanding Git Sync in Kestra
Kestra offers two main approaches for syncing code from Git repositories:

#### NamespaceSync - Project-Specific Code Sync

Syncs files from a single Git directory to a specific namespace.

- **Best for:** Team-specific code, isolated projects.
- **Use when:** You want simple, focused syncing for one team/project.
- **Git structure:** Flat directory structure (e.g., `data-processing/`).
- **Scope:** Files are only available within the target namespace.
- **Example:** Your data engineering team's Python ETL scripts in `dev.testing` namespace.
- **Authentication:** Uses Git credentials only.

**When to use:** You have a simple project where all code belongs to one team/namespace.

#### TenantSync - Multi-Namespace Code Distribution

Syncs files and flows from a structured Git repository to multiple namespaces simultaneously.

- **Best for:** Organization-wide code distribution, shared utilities.
- **Use when:** You need to distribute code across multiple namespaces from a single source.
- **Git structure:** Namespace-based directory structure (e.g., `<namespace>/files/`, `<namespace>/flows/`).
- **Scope:** Syncs to ALL namespaces found in your Git repository structure.
- **Example:** Shared validation libraries in `common/files/` → `common` namespace, team-specific code in `dev.testing/files/` → `dev.testing` namespace.
- **Authentication:** Requires both Git credentials AND Kestra API credentials.

**When to use:** You have multiple teams/namespaces and want centralized GitOps management of all code.

> [!IMPORTANT]
> **Key Difference:** NamespaceSync is simpler and syncs one directory to one namespace. TenantSync reads your entire repository structure and creates/updates files in multiple namespaces based on the folder names. It distributes files to their respective namespaces based on your Git folder structure.

👉 More info about [TenantSync and NamespaceSync](https://kestra.io/docs/version-control-cicd/git#git-tenantsync-and-namespacesync).

### Prerequisites
Before starting, ensure you have:

- A GitHub account (free account is sufficient)
- Git installed on your machine
- Your Kestra instance running with port-forwarding active

### Step 1: Create a GitHub Repository

First, let's create a repository to hold our code.
1. Go to https://github.com and sign in
1. Click the + icon in the top right, then select "New repository"
1. Configure your repository:
    - Repository name: kestra-demo
    - Description: "Demo project for Kestra Git sync"
    - Visibility, .gitignore, and license as you want (for this demo, we won't add a license, use a private repo without a .gitignore file).
4. Click "Create repository"

Perfect! Here's the revised Step 2:

### Step 2: Set Up Your Repository Structure Locally
Now let's create the repository structure on your local machine and connect it to GitHub.
We'll create a structure that works for both NamespaceSync and TenantSync.

1. Create a new directory for the project and initialize Git:
```bash
mkdir kestra-git-demo
cd kestra-git-demo
git init
```
2. Create the folder structure:
```bash
# For NamespaceSync (simple structure)
mkdir -p data-processing

# For TenantSync (namespace-based structure)
mkdir -p dev.testing/files
mkdir -p common/files
```
3. Create the file `process_sales.py` in `data-processing` with the content:
```python
import pandas as pd

def process_sales_data():
    print("Running from GitHub-synced code!")
    
    data = {
        'product': ['Laptop', 'Mouse', 'Keyboard'],
        'quantity': [50, 200, 150],
        'price': [999.99, 29.99, 79.99]
    }
    df = pd.DataFrame(data)
    df['revenue'] = df['quantity'] * df['price']
    
    df.to_csv('sales_output.csv', index=False)
    
    total = df['revenue'].sum()
    print(f"✓ Total revenue: ${total:,.2f}")
    return total

if __name__ == "__main__":
    process_sales_data()
```
4. Create the file `process_orders.py` in `dev.testing/files/` with the content:
```python
import pandas as pd

def process_orders():
    print("Running from GitHub-synced code via TenantSync!")
    
    data = {
        'order_id': [1, 2, 3],
        'customer': ['Alice', 'Bob', 'Charlie'],
        'amount': [150.00, 200.50, 99.99]
    }
    df = pd.DataFrame(data)
    
    df.to_csv('orders_output.csv', index=False)
    
    total = df['amount'].sum()
    print(f"✓ Total orders: ${total:,.2f}")
    return total

if __name__ == "__main__":
    process_orders()
```
5. Create the file `validator.py` in `common/files` with the content:
```python
def validate_phone(phone):
    """Simple phone validator - shared utility"""
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) >= 10

if __name__ == "__main__":
    print(f"Phone valid: {validate_phone('+1-555-123-4567')}")
```
5. Verify the structure was created correctly:
```
├── data-processing
│   └── process_sales.py
├── dev.testing
│   └── files
│       └── process_orders.py
└── common
    └── files
        └── validator.py 
```

![Required folder structure.](/images/kestra-git-demo-folder-structure.png)

7. Connect Your Local Repository to GitHub:
Replace YOUR-USERNAME with your actual GitHub username:
```bash
git remote add origin https://github.com/YOUR-USERNAME/kestra-demo.git
```
Verify the remote was added:
```bash
git remote -v
```

You should see:
```bash
origin  https://github.com/YOUR-USERNAME/kestra-demo.git (fetch)
origin  https://github.com/YOUR-USERNAME/kestra-demo.git (push)
```
7. Add, commit, and push your files to GitHub:
```bash
git add .
git commit -m "Initial commit: Add data processing and shared utilities"
git branch -M main
git push -u origin main
```
> [!NOTE]
> If this is your first time pushing to this repository, you may need to authenticate with GitHub. Follow the prompts or use a personal access token if password authentication is disabled.

### Step 3: Create a GitHub Personal Access Token
Kestra needs authentication to access your repository.

> [!NOTE]
> The following access token is just an example. Make sure to properly configure your tokens for your use case and to be compliant with your companies' requirements.

1. In GitHub, click your profile picture → `Settings`
1. Scroll down and click `Developer settings` (bottom left)
1. Click `Personal access tokens` → `Tokens (classic)`
1. Click `Generate new token` → `Generate new token (classic)`
![New personal access token page in GitHub.](/images/pat-github.png)
1. Configure your token:
Note: "Kestra Demo Access"
Expiration: 30 days (or as needed)
Scopes: Check `repo` (Full control of private repositories)
1. Click `Generate token` at the bottom
1. Important: Copy the token immediately (it starts with ghp_). You won't be able to see it again!

### Step 4: Store GitHub Token and User Credentials in Your Config
> [!NOTE]
> If you have the enterprise edition, you can also store the token in the secrets of the namespace which simplifies this step (`Namespace` -> select your namespace -> `Secrets`).

If you use the open-source option, do the following:

> [!CAUTION]
> Make sure to put the `.env` and `.env_encoded` files into your `.gitignore` file.

1. Create an environment file (`.env`) with this content:
```
GITHUB_TOKEN=[YOUR_GITHUB_PERSONAL_ACCESS_TOKEN]
KESTRA_USER=[YOUR_KESTRA_USER]
KESTRA_PASSWORD=[YOUR_KESTRA_PASSWORD]
```
2. Use the encode_secrets.sh file to create a base64 encoded secrets file.
You should see an `.env_encoded` file which contains the base64 encoded secret.

3. Create a Kubernetes Secret from your `.env_encoded` file with this command:
```bash
kubectl create secret generic kestra-secrets --from-env-file=.env_encoded
```
4. Verify it was created by running:
```bash
kubectl describe secret kestra-secrets
```
5. Update your `config.yml` to reference this Kubernetes Secret by adding this entry in the common section (on the same level as `extraEnv` before):
```yaml
  extraEnvFrom:
    - secretRef:
        name: kestra-secrets
```

👉 More info about [secrets in the open source version](https://kestra.io/docs/concepts/secret#secrets-in-the-open-source-version).

### Step 5: Upgrade Kestra
Run this (or uninstall and recreate Kestra as described before):
```bash
helm upgrade kestra kestra/kestra -f config_github.yml

kubectl get pods -l app.kubernetes.io/name=kestra -w
```
Wait for `2/2 Running`.

### Set Up NamespaceSync (Project-Specific Code)
Let's sync the data-processing folder to a specific namespace.

In Kestra UI, create this new flow:
```yaml
id: sync-project-code
namespace: dev.testing

tasks:
  - id: sync_code
    type: io.kestra.plugin.git.SyncNamespaceFiles
    gitDirectory: data-processing
    namespace: dev.testing
    url: https://github.com/YOUR-USERNAME/kestra-demo.git
    branch: main
    username: YOUR-USERNAME
    password: "{{ secret('GITHUB_TOKEN') }}"
    
triggers:
  - id: sync_schedule
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "*/15 * * * *"  # Sync every 15 minutes
```

> [!IMPORTANT]
> Replace `YOUR-USERNAME` with your actual GitHub username.

This will sync the code with GitHub every 15 minutes.

Lastly, click **Save** and **Execute** to run the sync immediately.

#### Check if the file was synced

If there were no errors, go to your namespace and check the `Files` menu. You should see the synced files (see screenshot below):

![Synced namespace files](/images/synced-namespace-files.png)

Now the file can be used in other flows.

#### Update Your Code

Do a small change to `process_sales.py` like adding an additional print-statement. Commit and push the changes and wait for 15 minutes or manually trigger the flow and the file stored in the namespace should also be updated.

👉 More info about [NamespaceSync](https://kestra.io/plugins/plugin-git/io.kestra.plugin.git.namespacesync).


### Show that the deletion of files also works 

Add this line below the password in the flow's task. It'll remove everything else from the namespace :D
``` delete: true ```

### Set up TenantSync
TenantSync synchronizes files and flows across ALL namespaces in your tenant. Unlike NamespaceSync, it requires API authentication and expects a specific folder structure.

#### Understanding the Structure

TenantSync expects your Git repository to follow this pattern:
```
<namespace>/
  ├── flows/        # Flow YAML definitions (optional)
  └── files/        # Namespace files (scripts, configs)
```  

We've already created this structure:
- `dev.testing/files/process_orders.py` - Project-specific file
- `common/files/validator.py` - Shared utility

#### Create the TenantSync Flow
In Kestra UI, create a new flow in the `system` namespace:

```yaml
id: sync-tenant-code
namespace: system

tasks:
  - id: sync_tenant
    type: io.kestra.plugin.git.TenantSync
    sourceOfTruth: GIT
    whenMissingInSource: KEEP
    url: https://github.com/YOUR-USERNAME/kestra-git-demo.git
    branch: main
    username: YOUR-USERNAME
    password: "{{ secret('GITHUB_TOKEN') }}"
    kestraUrl: "http://localhost:8080"
    auth:
      username: "{{ secret('KESTRA_USER') }}"
      password: "{{ secret('KESTRA_PASSWORD') }}"
    
triggers:
  - id: sync_schedule
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "*/15 * * * *"
```

> [!IMPORTANT]
> - Replace YOUR-USERNAME with your actual GitHub username.
> - The kestraUrl uses localhost because the task runs inside the Kubernetes cluster.

> [!IMPORTANT]
> You need to have the listed namespaces of your GitHub repo (dev.testing, common, data-processing). If you use the Open Source edition, you cannot create them via Kestra UI. However, you can run a simple flow (see Run Python Code) with the required namespace and this will generate the namespace for you.

Click "Execute".

If there were no errors, go to your namespace and check the `Files` menu. You should see the synced files (see screenshot below):

![Synced namespace files](/images/synced-tenantsync-files.png)

Now the file can be used in other flows and synced when changes happen.

👉 More info about [TenantSync](https://kestra.io/plugins/plugin-git/io.kestra.plugin.git.tenantsync).

## Reusable Flows with Subflows

Another feature of Kestra are Subflows. Often core business logic needs to be repeated in several places which would require us to break the DRY (Don't repeat yourself) principle. It'd be harder to maintain since a change to the logic needs to be made in several places.

Additionally, we often want to have a more modular separation where on flow orchestrates multiple subtasks to do certain things. 

In both cases, Subflows allow us to split and reuse our logic.

Here is how to use Subflows:
1. Create your subflow that will get some orders data from a CSV via https.
```yaml
id: critical_service
namespace: dev.testing
tasks:
  - id: return_data
    type: io.kestra.plugin.jdbc.duckdb.Query
    sql: |
      INSTALL httpfs;
      LOAD httpfs;
      SELECT sum(total) as total, avg(quantity) as avg_quantity
      FROM read_csv_auto('https://huggingface.co/datasets/kestra/datasets/raw/main/csv/orders.csv', header=True);
    store: true
outputs:
  - id: some_output
    type: STRING
    value: "{{ outputs.return_data.uri }}"
```
2. Create your parent flow that uses the subflow and logs the output.
```yaml
id: parent_service
namespace: dev.testing

tasks:
  - id: subflow_call
    type: io.kestra.plugin.core.flow.Subflow
    namespace: dev.testing
    flowId: critical_service
    wait: true
    transmitFailed: true
  - id: log_subflow_output
    type: io.kestra.plugin.scripts.shell.Commands
    taskRunner:
      type: io.kestra.plugin.core.runner.Process
    commands:
      - cat "{{ outputs.subflow_call.outputs.some_output }}"
```
3. Execute the parent flow (`parent_service`) which will generate an output file and also log the values to the console.

A few things to note here:
- The parent flow waits for the subflow to be finished before proceeding to the task `log_subflow_output`. You can also let them run at the same time with `wait: false`. But in this case this makes obviously no sense.
- The shown text for your subflow task can differ from it's name. In the Kestra UI, the `id` property will be shown, while the `flowId` is the actual reference to the subflow.
- In the example, if the referenced subflow fails, the parent flow will also stop working (see `transmitFailed`). This can be changed, if later tasks don't require the previous flows to succeed. However, if set to true, then you also need `wait` to be set to true.

👉 More info about [Subflows](https://kestra.io/docs/workflow-components/subflows). 


## Create transformation from GCS to BigQuery - raw to clean

Create the BigQuery Datasets
```bash
bq --location=EU mk --dataset kestra-workspace-ak-lde-2025:raw

bq --location=EU mk --dataset kestra-workspace-ak-lde-2025:clean
```

## Create the script that reads from GCS and write into BigQuery

```yml
id: ecommerce_ingest_and_clean_with_errors
namespace: gcp.ecommerce

variables:
  projectId: "kestra-workspace-ak-lde-2025"
  input_bucket: "lde-my-kestra-workspace"
  location: "EU"

tasks:
  # --- 1. Load RAW data from GCS into BigQuery ---
  - id: load_raw
    type: io.kestra.plugin.gcp.bigquery.LoadFromGcs
    from:
      - "gs://{{ vars.input_bucket }}/data.csv"
    destinationTable: "{{ vars.projectId }}.raw.transactions_raw"
    format: CSV
    autodetect: true
    csvOptions:
      skipLeadingRows: 1
    writeDisposition: WRITE_TRUNCATE

  # --- 2. CLEAN table: cast only important fields + business rules ---
  - id: clean_data
    type: io.kestra.plugin.gcp.bigquery.Query
    projectId: "{{ vars.projectId }}"
    location: "{{ vars.location }}"
    sql: |
      CREATE OR REPLACE TABLE `{{ vars.projectId }}.clean.transactions` AS
      SELECT
        InvoiceNo,
        StockCode,
        Description,
        SAFE_CAST(Quantity AS INT64) AS Quantity,
        SAFE_CAST(UnitPrice AS FLOAT64) AS UnitPrice,
        SAFE_CAST(InvoiceDate AS TIMESTAMP) AS InvoiceDate,
        CustomerID,
        Country
      FROM `{{ vars.projectId }}.raw.transactions_raw`
      WHERE SAFE_CAST(Quantity AS INT64) > 0
        AND SAFE_CAST(UnitPrice AS FLOAT64) > 0
        AND InvoiceNo NOT LIKE 'C%';

  # --- 3. ERROR table: everything that failed clean conditions ---
  - id: error_data
    type: io.kestra.plugin.gcp.bigquery.Query
    projectId: "{{ vars.projectId }}"
    location: "{{ vars.location }}"
    sql: |
      CREATE OR REPLACE TABLE `{{ vars.projectId }}.clean.transactions_errors` AS
      SELECT *
      FROM `{{ vars.projectId }}.raw.transactions_raw`
      WHERE NOT (
        SAFE_CAST(Quantity AS INT64) > 0
        AND SAFE_CAST(UnitPrice AS FLOAT64) > 0
        AND InvoiceNo NOT LIKE 'C%'
      );
```

## Download larger dataset

[NYC Yellow Cab Dataset](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)


Create the BigQuery Datasets
```bash
bq --location=EU mk --dataset kestra-workspace-ak-lde-2025:YellowCab
```


## Flow to cretae the processing - sequentially

```bash
id: yellow_cab_ingest_raw
namespace: gcp.yellowcab

variables:
  bucket: "lde-my-kestra-workspace"

tasks:
  - id: list_files
    type: io.kestra.plugin.gcp.gcs.List
    from: "gs://{{ vars.bucket }}/yellow-cab/"
    serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"

  - id: dump_blobs
    type: io.kestra.plugin.core.debug.Return
    format: |
      OUTPUT BLOBS:
      {{ outputs.list_files.blobs }}

  - id: foreach_file
    type: io.kestra.plugin.core.flow.ForEach
    values: "{{ outputs.list_files.blobs }}"
    tasks:
      - id: load
        runIf: "{{ taskrun.value | jq('.size') | first > 0 }}"
        type: io.kestra.plugin.gcp.bigquery.LoadFromGcs
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        from:
          - "{{ taskrun.value | jq('.uri') | first }}"
        destinationTable: "kestra-workspace-ak-lde-2025.YellowCab.raw_data"
        format: PARQUET
        location: "EU"
        writeDisposition: WRITE_APPEND
```

## Add paralell processing

```
concurrencyLimit: 5
```

get the csv for identification of zones
https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page


## Create a widely parallel task with subtask

### Main task:

```
id: yellow_cab_main
namespace: gcp.yellowcab

variables:
  bucket: "lde-my-kestra-workspace"

tasks:

  # ---------------------------------------------------------
  # 1. LIST INPUT FILES
  # ---------------------------------------------------------
  - id: list_files
    type: io.kestra.plugin.gcp.gcs.List
    from: "gs://{{ vars.bucket }}/yellow-cab/"
    serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"


  # ---------------------------------------------------------
  # 2. PARALLEL GCS -> BIGQUERY RAW INGESTION
  # ---------------------------------------------------------
  - id: foreach_file
    type: io.kestra.plugin.core.flow.ForEach
    values: "{{ outputs.list_files.blobs }}"
    concurrencyLimit: 5
    tasks:
      - id: load_raw
        type: io.kestra.plugin.gcp.bigquery.LoadFromGcs
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        from:
          - "{{ taskrun.value | jq('.uri') | first }}"
        destinationTable: "kestra-workspace-ak-lde-2025.YellowCab.raw_trips"
        format: PARQUET
        location: "EU"
        writeDisposition: WRITE_APPEND
        runIf: "{{ taskrun.value | jq('.size') | first > 0 }}"


  # ---------------------------------------------------------
  # 3. TRIGGER SUBFLOW (BigQuery transformations)
  # ---------------------------------------------------------
  - id: process_raw_data
    type: io.kestra.plugin.core.flow.Subflow
    namespace: gcp.yellowcab
    flowId: yellow_cab_bq_processing
    wait: true


  # ---------------------------------------------------------
  # 4a. COPY EACH FILE TO ARCHIVE (PER-FILE) 
  # ---------------------------------------------------------
  - id: foreach_copy
    type: io.kestra.plugin.core.flow.ForEach
    values: "{{ outputs.list_files.blobs }}"
    concurrencyLimit: 10
    tasks:
      - id: debug_blobs
        type: io.kestra.plugin.core.debug.Return
        format: |
          URI: {{ taskrun.value | jq('.uri') | first }}
          NAME: {{ taskrun.value | jq('.name') | first }}
          SIZE: {{ taskrun.value | jq('.size') | first }}
            
      - id: copy_to_archive
        type: io.kestra.plugin.gcp.gcs.Copy
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        from: "{{ taskrun.value | jq('.uri') | first }}"
        to: "gs://{{ vars.bucket }}/yellow-cab-archive/{{ taskrun.value | jq('.name') | first | split(\"/\") | last }}"
        runIf: "{{ taskrun.value | jq('.size') | first > 0 }}"

  # 🔥 BARRIER — IMPORTANT!?
  - id: wait_for_copy
    type: io.kestra.plugin.core.debug.Return
    format: "Copy completed"

# ---------------------------------------------------------
  # 4b. DELETE EACH FILE (PER-FILE)
  # ---------------------------------------------------------
  - id: foreach_delete
    type: io.kestra.plugin.core.flow.ForEach
    values: "{{ outputs.list_files.blobs }}"
    concurrencyLimit: 10
    tasks:
      - id: delete_file
        type: io.kestra.plugin.gcp.gcs.Delete
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        uri: "{{ taskrun.value | jq('.uri') | first }}"
        runIf: "{{ taskrun.value | jq('.size') | first > 0 }}"
```

### Subtask

```
id: yellow_cab_bq_processing
namespace: gcp.yellowcab

variables:
  bucket: "lde-my-kestra-workspace"

tasks:

  # ---------------------------------------------------------
  # 0) LOAD TAXI ZONE LOOKUP FROM GCS INTO BIGQUERY
  # ---------------------------------------------------------
  - id: load_taxi_zones
    type: io.kestra.plugin.gcp.bigquery.LoadFromGcs
    serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
    from:
      - "gs://{{ vars.bucket }}/taxi_zone_lookup.csv"
    destinationTable: "kestra-workspace-ak-lde-2025.YellowCab.taxi_zones"
    format: CSV
    csvOptions:
      skipLeadingRows: 1
    autodetect: true
    writeDisposition: WRITE_TRUNCATE
    location: "EU"


  # ---------------------------------------------------------
  # 1) ENRICH RAW TRIPS WITH ZONE LOOKUP (JOIN ON PULocationID)
  # ---------------------------------------------------------
  - id: zone_classification
    type: io.kestra.plugin.gcp.bigquery.Query
    serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
    location: "EU"
    sql: |
      CREATE OR REPLACE TABLE
        `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone` AS
      SELECT
        t.*,
        z.Borough        AS pu_borough,
        z.Zone           AS pu_zone,
        z.service_zone   AS pu_service_zone
      FROM
        `kestra-workspace-ak-lde-2025.YellowCab.raw_trips` t
      LEFT JOIN
        `kestra-workspace-ak-lde-2025.YellowCab.taxi_zones` z
      ON
        t.PULocationID = z.LocationID;


  # ---------------------------------------------------------
  # 2) SPECIAL TRIP DETECTION (PARALLEL)
  # ---------------------------------------------------------
  - id: special_trips
    type: io.kestra.plugin.core.flow.Parallel
    tasks:

      # Suspiciously low fares
      - id: suspicious_trips
        type: io.kestra.plugin.gcp.bigquery.Query
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        location: "EU"
        sql: |
          CREATE OR REPLACE TABLE
            `kestra-workspace-ak-lde-2025.YellowCab.suspicious_trips` AS
          SELECT *
          FROM `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone`
          WHERE fare_amount < 3;

      # Very short trips
      - id: short_trips
        type: io.kestra.plugin.gcp.bigquery.Query
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        location: "EU"
        sql: |
          CREATE OR REPLACE TABLE
            `kestra-workspace-ak-lde-2025.YellowCab.short_trips` AS
          SELECT *
          FROM `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone`
          WHERE trip_distance < 0.5;

      # Ultra long trips
      - id: long_trips
        type: io.kestra.plugin.gcp.bigquery.Query
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        location: "EU"
        sql: |
          CREATE OR REPLACE TABLE
            `kestra-workspace-ak-lde-2025.YellowCab.long_trips` AS
          SELECT *
          FROM `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone`
          WHERE trip_distance > 40;

      # Invalid GPS / bad location
      - id: invalid_gps
        type: io.kestra.plugin.gcp.bigquery.Query
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        location: "EU"
        sql: |
          CREATE OR REPLACE TABLE
            `kestra-workspace-ak-lde-2025.YellowCab.invalid_gps` AS
          SELECT *
          FROM `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone`
          WHERE PULocationID IS NULL
             OR PULocationID = 0;


  # ---------------------------------------------------------
  # 3) AGGREGATIONS (PARALLEL)
  # ---------------------------------------------------------
  - id: aggregations
    type: io.kestra.plugin.core.flow.Parallel
    tasks:

      # Trips grouped by borough
      - id: trips_per_borough
        type: io.kestra.plugin.gcp.bigquery.Query
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        location: "EU"
        sql: |
          CREATE OR REPLACE TABLE
            `kestra-workspace-ak-lde-2025.YellowCab.trips_per_borough` AS
          SELECT pu_borough, COUNT(*) AS trips
          FROM `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone`
          GROUP BY pu_borough;

      # Average fare per borough
      - id: avg_fare_per_borough
        type: io.kestra.plugin.gcp.bigquery.Query
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        location: "EU"
        sql: |
          CREATE OR REPLACE TABLE
            `kestra-workspace-ak-lde-2025.YellowCab.avg_fare_per_borough` AS
          SELECT pu_borough, AVG(fare_amount) AS avg_fare
          FROM `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone`
          GROUP BY pu_borough;

      # Trips by hour of day
      - id: trips_by_hour
        type: io.kestra.plugin.gcp.bigquery.Query
        serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
        location: "EU"
        sql: |
          CREATE OR REPLACE TABLE
            `kestra-workspace-ak-lde-2025.YellowCab.trips_by_hour` AS
          SELECT
            EXTRACT(HOUR FROM tpep_pickup_datetime) AS hour,
            COUNT(*) AS trips
          FROM `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone`
          GROUP BY hour;


  # ---------------------------------------------------------
  # 4) FINAL CURATED TABLE
  # ---------------------------------------------------------
  - id: curated_table
    type: io.kestra.plugin.gcp.bigquery.Query
    serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
    location: "EU"
    sql: |
      CREATE OR REPLACE TABLE
        `kestra-workspace-ak-lde-2025.YellowCab.trips_cleaned` AS
      SELECT *
      FROM `kestra-workspace-ak-lde-2025.YellowCab.trips_with_zone`
      WHERE trip_distance > 0
        AND fare_amount > 0
        AND pu_borough IS NOT NULL;
```








My old load_single_file flow
```bash
id: load_single_file
namespace: gcp.yellowcab

inputs:
  - id: file_uri
    type: STRING

tasks:
  - id: load
    type: io.kestra.plugin.gcp.bigquery.LoadFromGcs
    from:
      - "{{ inputs.file_uri }}"
    destinationTable: "kestra-workspace-ak-lde-2025.YellowCab.trips"
    format: PARQUET
    location: "EU"
    writeDisposition: WRITE_APPEND

```

```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

```
helm install postgres bitnami/postgresql \
  --set auth.username=kestra \
  --set auth.password=kestra \
  --set auth.database=kestra
```
```
helm install redis bitnami/redis \
  --set architecture=standalone \
  --set auth.enabled=false
```

```
helm install kestra kestra/kestra -f config_github.yml
helm upgrade --install kestra kestra/kestra-distributed -f minimal_distributed.yml
```




## Clean up

In order to clean up the changes, run the following commands:

```bash
helm uninstall kestra
minikube delete
gsutil -m rm -r gs://your-bucket-name
gcloud projects delete $PROJECT_ID
```

> [!NOTE]
> Replace `your-bucket-name` with your actual GCP bucket name.


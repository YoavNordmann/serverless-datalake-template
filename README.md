# serverless-datalake-template
A Data Lake with OpenFaas on K3s, showing datalake pipelines using the serverless architecture

Lately I was confronted with a problem of creating a Data Lake. This was not such a big task considering you can use any of the big players such as AWS, Google, Azure and others. Each one of them has some basic setup for you to create a starting model of a Data Lake with minimal effort. The catch was I was supposed to build a simple working model of a Data Lake ***without*** using proprietary technology.

And the game was on.

## The Goal
So I set out to create a very simplistic model of a Data Lake. The three zones are as follows

1. Raw Data (Bronze Zone)
2. Staging Data (Silver Zone)
3. Processed Data (Gold Zone)

Furthermore, I wanted the ingestion of the data to be agnostic to the zones. This means I need something like a Transient Zone for incoming data.

After some inspiration from [AWS Glue](https://aws.amazon.com/glue/) I understood that the serverless architecture would be a great solution to my problem. Furthermore, I needed some messaging queue in order for the pipeline to be truly asynchronous and scalable the way I intended it to be.


## The Design
I would need 4 functions to handle each phase in my pipeline:
1. Data ingestion
2. Write Data to Raw Data
3. Write Data to Staging Data
4. Write Data to Processed Data

The first function would be a REST interface by which the producer is sending the data into the pipeline. Once received, it would write the data to a topic on the NATS messaging service. Sort of like a Pub-Sub Model. Each of the other 3 functions listen for events on specific topics on a messaging queue, firing when it is their turn to perform the task in a series of tasks. Thus we have successfully created a data pipeline for persisting data in a data lake architecture type. 

As an example, if I am collecting data on click-events the pipeline would look as follows:

| Trigger Type | Address | Function | Notify Topic |  |
|--|--|--|--|--|
| REST | http://xyz.io/clickevent | Function 1 | clickevent.ingest |
| Message | clickevent.ingest | Function 2 | clickevent.rawdata |
| Message | clickevent.rawdata | Function 3 | clickevent.stagingdata |
| Message | clickevent.stagingdata | Function 4 | - |

Each Function number corresponding to the above mentioned description of the function. Turns out, each function writes to a topic describing the processing detail of the function itself. That sounds right to me.

So what about the implementation ?


## The Implementation
After some digging and researching I came across the The [OpenFaas](https://www.openfaas.com/) framework. A mature serverless framework which comes with [NATS](https://nats.io/), an open source messaging system, incorporated. On top of that, a friend made me aware of this really cool project called [K3s](https://k3s.io/), a lightweight Kubernetes distribution built for IoT & Edge computing. Helping me keeping the overview on my K8s, I used [k9s](https://k9scli.io/), a terminal based UI to interact with your Kubernetes cluster.

The technological stack was set. I was hyped, hooked and ready to rock !

### K3s

I did not want to install K3s as a deamon, so I installed the  [K3s binary](https://github.com/rancher/k3s/releases/) without the installation script as described in Ranchers well written documentation on [installation options](https://rancher.com/docs/k3s/latest/en/installation/install-options/), specifically "Installing K3s from the Binary"

After installing the binary, all I had to do was run the following commands:
```
sudo k3s server --write-kubeconfig-mode 644
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

Alternatively, I could have used the [K3d](https://github.com/rancher/k3d) utility, another really cool tool, which runs a K8s cluster inside a docker conatiner (!!!). 
To use/run K8s in this manner I would used the k3d binary and run the following command:
```
k3d create --publish 31112:31112
```
  

### Openfaas

Although I used the installation method using the openfaas projects yml files, I do recommend using helm charts. The exact way of installing the openfaas helm chart can be found [here](https://github.com/openfaas/faas-netes/blob/master/chart/openfaas/README.md). In short, the follwing commands will install openfaas on your K8s cluster:

```
# helm repo add openfaas https://openfaas.github.io/faas-netes/
# helm repo update \
 && helm upgrade openfaas --install openfaas/openfaas \
    --namespace openfaas  \
    --set functionNamespace=openfaas-fn
# PASSWORD=$(kubectl -n openfaas get secret basic-auth -o jsonpath="{.data.basic-# auth-password}" | base64 --decode) && \
# echo "OpenFaaS admin password: $PASSWORD"    
```

After a successful installation you can use the password to log into the administration console of openfaas: http://localhost:31112

Another utility you will need is the [faas-cli](https://docs.openfaas.com/cli/install/) which can be installed quite easily. In order to get the *faas-cli* working you need to set the *OPENFAAS_URL* environment variable like so:
```
export OPENFAAS_URL=http://localhost:31112
```

### Functions

And now the real fun begins.
For the data ingestion function we need to get some newer openfaas templates:
```
faas template pull https://github.com/openfaas-incubator/python-flask-template
```
And now we create the function:
```
faas-cli new --lang python3-http clickevent-ingest
```
For the other three function we use the basic python3 templates, as they do not listen for http events, rather for events on a topic on NATS:
```
faas-cli new --lang python3 clickevent-rawdata
faas-cli new --lang python3 clickevent-staging
faas-cli new --lang python3 clickevent-processed
```	

At this point you will also have 4 different yml files in the same folder, each one named after the function created. I suggest you merge those files into 1 yml file and call it: *"clickevent-pipeline.yml"*. Don't worry, you can still manipulate individual functions even tho they are in the same yml file.

### NATS configuration

In order to work with NATS the way i want, i have to do the following thigs:
1. Add a NATS client dependency to the functions
2. connect the functions to listen to specific topics
3. Configure NATS to invoke a function for specific topics

#### NATS client 
I used the official [NATS Python client](https://github.com/nats-io/nats.py), asyncio-nats-client. This means, i had to add the following to the requirements.txt file of each function.
```
asyncio-nats-client==0.10.0
```
Using this api, I was able to connect and send messages to NATS.

#### Connect Functions to topics
For those functions which listen on a topic from NATS, I had to add an *annotation* section in the function description of the yml file like so:
```
annotations:
	topic: <topic-name>
``` 
topic name being different for each one of course.

#### Configure NATS Connector
This is the tricky part which took me some time to figure out. Although OpenFaas supports different function [triggers](https://docs.openfaas.com/reference/triggers/), the NATS trigger is not a standard one. In order to make this work you need another deployment to K8s, the [nats-connector](https://github.com/openfaas-incubator/nats-connector). And in order to make your own topics work, you first need to downlod the [nats-connector deployment file](https://github.com/openfaas-incubator/nats-connector/blob/master/yaml/kubernetes/connector-dep.yaml) and make you changes there, specifically in the topics section:
```
- name: topics
  value: "clickevent.ingest,clickevent.rawdata,clickevent.stagingdata"	
```
There are more options to control behavior in this file which I will not get into. Also, it seems this is a deployment I would need to share between different pipelines, unless I have such a deployment for each separate pipeline.

Deploy this yml file to K8s:
```
kubectl apply -f connector-dep.yaml
```
and you are set to go.

## Deployment
All you need to do now is write your logic into each function, making sure each function writes to its designated topic on NATS after completion of the task. Once finished you can deply your function by just running the following command:
```
faas-cli up -f ./clickevent-pipeline.yml
```
Now, in order to invoke your pipeline just send a POST command to your first function, the one listening on a REST trigger and see the magic happen:
```
curl --request POST \
  --url http://localhost:31112/function/clickevent-ingest \
  --header 'content-type: application/json' \
  --data '{
	"type":"clickevent",
	"mousebutton": "left",
	"isnew": true
}'
```

## Conclusion
This has been a wonderful journey with a lot of new tech and seeing all of them coming together is a real joy. Besides that, I think the serverless architecture has proven itself to be a very effective and versatile tool which can be applied in many different ways, this being just on of them. Using Serverless on K8s frees you from any sort of vendor lock-in which I can only recommend.

Not all went as smooth as described in this blog and I do wish sometimes there was more information on this subject, but here is my help in that regard.

You can find my working demo on [github](https://github.com/YoavNordmann/serverless-datalake-template)
 
I would like to mention some great blogs which got me started:
 - [Setup OpenFaaS on k3s with private docker registry](https://medium.com/@robertdiers/setup-openfaas-on-k3s-with-local-docker-registry-7a84ebb54a6f)
 - [Deploy your first Serverless Function to Kubernetes](https://itnext.io/deploy-your-first-serverless-function-to-kubernetes-232307f7b0a9)
 - [Deployment guide for Kubernetes](https://docs.openfaas.com/deployment/kubernetes/)


Enjoy!
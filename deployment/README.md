# AWS EKS deployment plan

AKS is Azure; for your AWS account the Kubernetes service is **Amazon EKS**.

## Target architecture
GitHub -> GitHub Actions -> ECR (backend/frontend images) -> EKS Deployments -> AWS Load Balancer
                                                        -> Amazon RDS for MySQL

Keep the database outside Kubernetes in RDS for backups, patching and durable storage.

## Provisioning checklist
1. Choose an AWS region and create an ECR repository for backend and frontend.
2. Create an RDS MySQL instance in private subnets. Restrict its security group to the EKS worker/node security group.
3. Create an EKS cluster and managed node group. For a first deployment, use `eksctl` from your local machine.
4. Install/configure `kubectl`, `eksctl`, and AWS CLI; run `aws eks update-kubeconfig --region REGION --name CLUSTER_NAME`.
5. Store database URL and SECRET_KEY in Kubernetes Secrets (prefer AWS Secrets Manager + External Secrets for production).
6. Apply Kubernetes manifests after replacing image URIs and secret values.
7. Install AWS Load Balancer Controller, configure ingress, Route 53 DNS and ACM TLS certificate.

## Example cluster creation (costs apply)
Install AWS CLI, eksctl and kubectl first, configure `aws configure`, then:
```bash
eksctl create cluster --name todo-eks --region ap-south-1 --nodes 2 --node-type t3.medium
aws eks update-kubeconfig --region ap-south-1 --name todo-eks
kubectl get nodes
```
This creates billable resources. Check current EKS, EC2, load balancer and NAT gateway pricing before running. Delete when finished:
```bash
eksctl delete cluster --name todo-eks --region ap-south-1
```

## Build and push images
```bash
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin AWS_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
docker build -t todo-backend ./backend
docker tag todo-backend:latest AWS_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/todo-backend:latest
docker push AWS_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/todo-backend:latest
docker build -t todo-frontend ./frontend
docker tag todo-frontend:latest AWS_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/todo-frontend:latest
docker push AWS_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/todo-frontend:latest
```

## Deploy
Update image references in `k8s/` manifests, create the secret, then:
```bash
kubectl apply -f k8s/
kubectl get pods,svc,ingress
```
The included ingress is a starting template; AWS Load Balancer Controller and its IAM permissions must be installed/configured before it will provision an ALB.

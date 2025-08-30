# FinAnalyze: Bank Statement OCR and Analysis

FinAnalyze is a web application designed to help users process and analyze their bank statements. It leverages Optical Character Recognition (OCR) to extract transactional data from PDF and image-based bank statements, categorizes transactions, and provides tools for financial overview.

## Features

*   **PDF/Image OCR**: Extract data from various bank statement formats using Tesseract OCR.
*   **Transaction Parsing**: Automatically identifies and parses transaction details (date, description, amount).
*   **Data Export**: Export processed transaction data in formats like CSV or JSON.
*   **User Authentication**: Secure user registration and login using Flask-JWT-Extended.
*   **Custom Database Migrations**: Manage database schema changes with a custom Python migration runner.
*   **Containerized Deployment**: Ready for deployment using Docker and Kubernetes (Kind for local development).

## Technical Stack

*   **Backend**: Flask (Python) with Flask-SQLAlchemy for ORM.
*   **Database**: PostgreSQL.
*   **OCR**: `pytesseract`, `pdf2image`, `Pillow` for image processing.
*   **Data Processing**: `pandas` for data manipulation.
*   **Authentication**: Flask-JWT-Extended for token-based authentication.
*   **Frontend**: Flask (serving HTML, CSS, JavaScript) with vanilla JavaScript for client-side interactions.
*   **Deployment**: Docker, Kubernetes (Kind).

## Architecture

FinAnalyze follows a monolithic architecture where both the backend API services and frontend static files are served by Flask applications. OCR processing is handled server-side by the backend.

*   **`db/`**: Contains the PostgreSQL database setup, custom migration scripts, and its Dockerfile.
*   **`backend/`**: Houses the Flask API server, database models, authentication logic, and OCR processing integration. It includes its own Dockerfile.
*   **`frontend/`**: Contains the Flask application for serving static frontend assets (HTML, CSS, JavaScript) and handling user interactions by communicating with the backend API. It includes its own Dockerfile.
*   **`k8s/`**: Kubernetes manifests for deploying the `db`, `backend`, and `frontend` services on a Kind cluster.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine using Docker and Kubernetes with Kind.

### Prerequisites

Before you begin, ensure you have the following installed:

*   [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
*   [Docker Desktop](https://www.docker.com/products/docker-desktop) (includes Docker Engine and Docker Compose)
*   [Kind (Kubernetes in Docker)](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
*   [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/FinAnalyze.git
cd FinAnalyze
```

### 2. Build Docker Images

Navigate to the `backend/` and `frontend/` directories and build their respective Docker images. Ensure you tag them as specified for Kubernetes deployment.

```bash
# Build backend image
cd backend
docker build -t finanalyze-backend:latest .
cd ..

# Build frontend image
cd frontend
docker build -t finanalyze-frontend:latest .
cd ..
```

### 3. Set up Kind Cluster

#### Create a Kind Cluster

If you don't have a Kind cluster running, create one:

```bash
kind create cluster --name finanalyze-cluster
```

#### Load Docker Images into Kind

Load the built Docker images into your Kind cluster. This makes the images available for your deployments without needing a public registry.

```bash
kind load docker-image finanalyze-backend:latest --name finanalyze-cluster
kind load docker-image finanalyze-frontend:latest --name finanalyze-cluster
```

### 4. Deploy to Kubernetes

Apply all the Kubernetes manifests in the `k8s/` directory. The order is important to ensure dependencies are met.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/db-configmap.yaml
kubectl apply -f k8s/db-secret.yaml
kubectl apply -f k8s/db-persistentvolumeclaim.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/db-service.yaml
kubectl apply -f k8s/backend-secret.yaml
kubectl apply -f k8s/backend-configmap.yaml
kubectl apply -f k8s/backend-persistentvolumeclaim.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-configmap.yaml
kubectl apply -f k8s/frontend-persistentvolumeclaim.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
```

### 5. Verify Deployment

Check the status of your pods, deployments, and services to ensure everything is running correctly.

```bash
kubectl get pods -n bank-ocr
kubectl get deployments -n bank-ocr
kubectl get services -n bank-ocr
```

### 6. Access the Frontend

Since the `frontend-service` is of type `NodePort`, you can access it via the IP address of your Kind cluster's node and the assigned NodePort.

```bash
NODE_IP=$(kubectl get nodes -o jsonpath='{ $.items[0].status.addresses[?(@.type=="InternalIP")].address }')
NODE_PORT=$(kubectl get service frontend-service -n bank-ocr -o jsonpath='{ .spec.ports[0].nodePort }')
echo "Frontend accessible at: http://${NODE_IP}:${NODE_PORT}"
```

Open the displayed URL in your web browser.

## Usage

1.  **Register/Login**: Navigate to the application in your browser. You'll need to implement registration and login functionality on the frontend to interact with the protected backend endpoints.
2.  **Upload Bank Statement**: Once logged in, upload a PDF or image file of a bank statement.
3.  **View Results**: The application will process the statement using OCR and display the extracted account information and transactions.
4.  **Export Data**: Export the parsed transaction data in CSV or JSON format.

## API Endpoints (Backend)

*   `POST /register`: Register a new user.
*   `POST /login`: Authenticate a user and receive a JWT access token.
*   `POST /ocr/process`: (Protected) Upload a bank statement for OCR processing.
*   `GET /protected`: (Protected) A sample protected endpoint.

## Future Enhancements

*   **Frontend Authentication Flow**: Implement a full user registration and login flow in the frontend to acquire and utilize JWT tokens for backend API calls.
*   **Database Schema Refinement**: Modify the `Transaction` model to use foreign keys for categories instead of string columns for better data integrity.
*   **N+1 Query Optimizations**: Optimize `to_dict()` methods in backend models to prevent N+1 query issues.
*   **Backend Cleanup Endpoint**: Implement a dedicated endpoint in the backend for cleaning up old uploaded files and processing results.
*   **Advanced Transaction Categorization**: Enhance transaction categorization logic.
*   **Error Handling and Logging**: Improve robust error handling and logging across all services.
*   **CI/CD Pipeline**: Automate building, testing, and deployment to Kubernetes.
*   **Observability**: Integrate monitoring and logging tools (e.g., Prometheus, Grafana, ELK stack).

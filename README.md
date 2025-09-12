# Personal Finance Tracker: Bank Statement OCR and Analysis

Personal Finance Tracker is a web application designed to help users process and analyze their bank statements. It utilizes Optical Character Recognition (OCR) to extract transactional data from PDF and image-based bank statements, categorizes transactions, and provides tools for financial overview.

## Features

- **PDF/Image OCR**: Extract data from various bank statement formats using Tesseract OCR.
- **Transaction Parsing**: Automatically identifies and parses transaction details (date, description, amount).
- **Data Export**: Export processed transaction data in CSV or JSON formats.
- **User Authentication**: Secure registration and login via Flask-JWT-Extended.
- **Custom Database Migrations**: Manage schema changes with a custom Python migration runner.
- **Containerized Deployment**: Ready for deployment using Docker and Kubernetes (Kind for local development).

## Technical Stack

- **Backend**: Flask (Python) with Flask-SQLAlchemy for ORM.
- **Database**: PostgreSQL.
- **OCR**: `pytesseract`, `pdf2image`, `Pillow` for image processing.
- **Data Processing**: `pandas` for data manipulation.
- **Authentication**: Flask-JWT-Extended for token-based authentication.
- **Frontend**: Flask serving HTML, CSS, JavaScript with vanilla JavaScript.
- **Deployment**: Docker, Kubernetes (Kind).

## Architecture

The application follows a monolithic architecture where both backend services and frontend static files are served by Flask. OCR processing is performed server-side.

- **`db/`**: PostgreSQL setup, migration scripts, and Dockerfile.
- **`backend/`**: Flask API, database models, authentication logic, OCR processing integration, and Dockerfile.
- **`frontend/`**: Serves static frontend assets and handles user interactions, containing its Dockerfile.
- **`k8s/`**: Kubernetes manifests for deploying services on a Kind cluster.

## Getting Started

Get the project running locally using Docker and Kubernetes with Kind.
### Prerequisites

Ensure you have the following installed:

- [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Kind (Kubernetes in Docker)](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)

### 1. Clone the Repository

```bash
git clone https://github.com/chuck1z/personal-finance-tracker.git
cd personal-finance-tracker
```

### 2. Build Docker Images

Navigate to the `backend/` and `frontend/` directories to build the Docker images.
```bash
# Build backend image
cd backend
docker build -t finance-tracker-backend:latest .
cd ..

# Build frontend image
cd frontend
docker build -t finance-tracker-frontend:latest .
cd ..
```

### Environment Variables

Create a `.env` file based on `.env.example` and set the following variables:

- `DATABASE_URL` – PostgreSQL connection string for the backend.
- `JWT_SECRET_KEY` – secret key used to sign JWTs.
- `BACKEND_API_URL` – URL where the frontend can reach the backend API.

### 3. Set up Kind Cluster

Create a Kind cluster if not already set up:
```bash
kind create cluster --name finance-tracker-cluster
```

#### Load Docker Images into Kind

Load the images into your Kind cluster for deployment.
```bash
kind load docker-image finance-tracker-backend:latest --name finance-tracker-cluster
kind load docker-image finance-tracker-frontend:latest --name finance-tracker-cluster
```

### 4. Deploy to Kubernetes

Apply all Kubernetes manifests from the `k8s/` directory in order:
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

Ensure everything is running smoothly:
```bash
kubectl get pods -n bank-ocr
kubectl get deployments -n bank-ocr
kubectl get services -n bank-ocr
```

### 6. Access the Frontend

Access it through the NodePort from your Kind cluster:
```bash
NODE_IP=$(kubectl get nodes -o jsonpath='{ $.items[0].status.addresses[?(@.type=="InternalIP")].address }')
NODE_PORT=$(kubectl get service frontend-service -n bank-ocr -o jsonpath='{ .spec.ports[0].nodePort }')
echo "Frontend accessible at: http://${NODE_IP}:${NODE_PORT}"
```

Open the displayed URL in your browser.

## Usage

1. **Register/Login**: Access the app in your browser for registration and login.
2. **Upload Bank Statement**: Upload a PDF or image file of a bank statement.
3. **View Results**: The application processes the statement using OCR and displays extracted data.
4. **Export Data**: Export data in CSV or JSON format.

## API Endpoints (Backend)

- `POST /register`: Register a new user.
- `POST /login`: Authenticate and receive a JWT token.
- `POST /ocr/process`: (Protected) Upload a statement for OCR processing.
- `GET /protected`: (Protected) Sample endpoint.

## Future Enhancements

- **Frontend Authentication Flow**: Implement full user registration/login using JWT.
- **Database Schema Refinement**: Use foreign keys for categories.
- **N+1 Query Optimizations**: Optimize backend queries.
- **Backend Cleanup Endpoint**: Implement file cleanup endpoint.
- **Advanced Transaction Categorization**: Improve categorization logic.
- **Error Handling and Logging**: Enhance error handling and logging.
- **CI/CD Pipeline**: Automate building, testing, deployment.
- **Observability**: Integrate tools like Prometheus, Grafana.


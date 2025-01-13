# Connectify - Django REST Framework Backend
Connectify is the backend for a social media platform designed to enhance user interaction with features like likes, comments, follows/unfollows, one-to-one and group chats, video calls, real-time notifications, and admin dashboards. This backend is built using Django REST Framework and deployed on AWS EC2 instances.

## Features
### Core Features
- **User Interaction**: Like, comment, follow/unfollow users, and interact with posts.
- **Chats**: One-to-one and group chat functionality powered by Django Channels and WebSockets.
- **Video Calling**: Integrated WebRTC for seamless one-to-one video calls.
- **Real-Time Notifications**: Instant updates for likes, comments, follows, and chat messages.
- **Google Authentication**: Login and signup via Google.
- **Admin Dashboard**: Manage users, analytics, and logs through an admin interface.

### Technical Highlights
- **Authentication**: Secure JWT-based authentication for APIs.
- **Scalability**: Redis is used for caching and managing asynchronous tasks.
- **Database**: PostgreSQL database running in a Docker container.
- **Deployment**: Hosted on AWS EC2 with services containerized using Docker and managed via Docker Compose.
- **Additional Features**: Includes analytics, user management, and detailed logging mechanisms.
- 
## 🛠 Installation
### Prerequisites
#### Install Docker: Ensure Docker and Docker Compose are installed on your system.
##### Clone the Repository:
```bash
git clone https://github.com/rahulxqmoz/SocialMediaAppBackend.git
cd connectify-backend
```
### Setting Up the Application
#### 1.Start Docker Services:
```bash
docker-compose up --build
```
This will:
- Build and start the backend, database, Redis, and Nginx services.
- Automatically run database migrations.

#### 2.Access the Application:

- Backend: http://localhost:8000
- Frontend (if running): Replace with the appropriate URL.
#### 3.Stop Services:

```bash
docker-compose down
```
#### 4.Run Tests:

```bash
docker-compose exec backend python manage.py test
```
## ⚙️ Docker Configuration
### Services Included
- **Django**: Backend API server.
- **Daphne**: ASGI server for WebSocket support.
- **Redis**: In-memory data store for caching and real-time operations.
- **PostgreSQL**: Relational database for data persistence.
- **Nginx**: Reverse proxy for routing requests.
### Key Configuration Files
- **docker-compose.yml**: Defines services and dependencies.
- **nginx.conf**: Configuration for Nginx reverse proxy.
- **Dockerfile**: Instructions to build the Django backend image.

## 🚀 Deployment
### Platform
AWS EC2: Backend hosted on an EC2 instance with Dockerized services.
### Steps to Deploy
#### 1.SSH into your EC2 instance.
#### 2.Clone the repository:
```bash
git clone https://github.com/rahulxqmoz/SocialMediaAppBackend.git
```
#### 3.Navigate to the project directory:
```bash
cd connectify-backend
```
#### 4.Start the Docker containers:
```bash
docker-compose up --build -d
```
## 🛡️ Security
- **Environment Variables**: Sensitive information (e.g., database credentials, secret keys) is managed using .env files.
- **Google OAuth**: Ensures secure login and signup functionality.
- **Redis**: Manages real-time data in a secure and isolated environment.

## 🔄 API Endpoints
### User Authentication
- `/register/`: User registration.
- `/login/`: User login.
- `/token/`: Obtain JWT token.
- `/token/refresh/`: Refresh JWT token.

### Profile Management
- `/profile/<user_id>/`: Fetch user profile.
- `/profile/update/`: Update profile details.
- `/password/update/`: Update user password.

### Admin
- `/admin/users/`: List all users (admin-only).
- `/admin/users/<pk>/block/`: Block a user (admin-only).

## 🧰 Tools & Technologies
- **Backend**: Django, Django REST Framework, Django Channels, Daphne.
- **Database**: PostgreSQL.
- **Cache**: Redis.
- **Authentication**: JWT, Google OAuth.
- **DevOps**: Docker, Nginx, AWS EC2.

## 📈 Future Enhancements
- **Group Video Calling**: Extend WebRTC integration for group calls.
- **Advanced Analytics**: Provide detailed usage metrics for admins.
- **AI-Powered Features**: Personalized recommendations for users.

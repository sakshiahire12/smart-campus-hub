# Smart Campus Hub

Smart Campus Hub is a web-based college service management system that allows students to submit campus service requests and track their status.

## Features

* Student login and logout
* Admin login and logout
* Role-based access control
* Create service requests
* Request date and time
* My Requests
* Recent Requests
* Request status tracking
* Admin dashboard
* Search and status filtering
* Dashboard statistics and analytics
* Form validation

## Technologies

* Python
* Flask
* SQLite
* HTML5
* CSS3
* JavaScript

## Main Workflow

Student Login → Create Request → Request Saved in Database → Admin Reviews Request → Admin Updates Status → Student Tracks Status

## Demo Login

Student:
`student / student123`

Admin:
`admin / admin123`

## How to Run

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Project Structure

```text
smart-campus-hub/
├── app.py
├── README.md
├── .gitignore
└── templates/
    ├── index.html
    ├── login.html
    ├── create_request.html
    ├── my_requests.html
    └── admin_dashboard.html
```

## Purpose

This project demonstrates a simple digital platform for managing common college service requests through one centralized system.

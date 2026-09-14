# System Architecture

BlueWaste follows a three-tier client-server architecture composed of the presentation layer, application layer, and data layer [16]. This architectural framework defines how users and system components interact, including hardware, software, and data resources that work together to support waste reporting, monitoring, and response operations.

The presentation layer contains both web and mobile user interfaces used by citizens, LGU administrators, and LGU workers. This layer includes the citizen reporting portal, interactive GIS map and heatmap interfaces, worker task views, and the administrative decision-support dashboard with analytical charts. The web platform provides map and analytics views for management operations, while the mobile platform supports field submission and status updates in on-site environments.

The application layer is composed of server-side services built with Node.js and Express [17]. It handles business logic such as report processing, role-based user authentication, report assignment, status lifecycle management, geolocation data handling, and notification dispatch. RESTful API endpoints connect frontend applications to backend services for secure and structured data exchange.

The data layer uses PostgreSQL as the centralized relational database, accessed through Prisma ORM [18][19]. It stores core records such as user accounts, geotagged waste reports, report images, cleanup status history, notifications, barangay and resort-area references, and analytics-ready data. External services are integrated in this architecture, including Cloudinary for media storage and a YOLO inference API for image analysis.

![Attached imaged]

**Figure 5: BlueWaste System Architecture Diagram**

In the operational flow, citizens submit waste reports from web or mobile clients using captured coordinates and photo evidence. The application layer validates and processes the submission, stores structured records in PostgreSQL, and links media resources through Cloudinary. The mapping services retrieve report coordinates to render markers and heatmaps, while the LGU dashboard generates trend summaries and spatial insights from stored data to support data-driven cleanup prioritization.



## Next Section

# Use Case Diagram
The Use Case Diagram illustrates the interaction between users and the BlueWaste system. The primary actors in the system are the Citizen, LGU Administrator, LGU Worker, and Resort Administrator, with YOLOv8 inference API, each accessing the system through their respective web or mobile interfaces as shown in Figure 6.

Actual Use Case Diagram Image

# Figure 6: BlueWaste’s Use Case Diagram

The diagram presents key system functions such as submitting and tracking waste reports, assigning reports to LGU workers, updating cleanup statuses, defining coverage areas, and viewing analytics and map visualizations. Image analysis is also represented as an automated system process triggered upon report submission. This diagram highlights how each user role interacts with the system to support effective waste monitoring and response coordination.


# Next Section

# Context Flow Diagram
The DFD Level 0, also known as the Context Diagram, presents an overview of the BlueWaste system and its interaction with external entities. It shows how the system communicates with Citizens, LGU Administrators, LGU Workers, and Resort Administrator, as illustrated in Figure 7.	

Actual level 0 context Diagram Image
Figure 7: BlueWaste’s Level 0 Context Diagram

The diagram highlights the flow of data such as waste report submissions, geolocation coordinates, photo uploads, status updates, and assignments between the system and its external stakeholders. It provides a high-level view of how the system collects, processes, and delivers information to support effective waste reporting and cleanup coordination.


# Next Section

# Level 1 Data Flow Diagram
The DFD Level 1 provides a detailed view of the internal processes of the BlueWaste system and how data flows between its components. It breaks down the main system into key processes such as user authentication, report submission and processing, image analysis, report assignment, status lifecycle management, notification dispatch, and analytics generation, as seen in Figure 8.

**Actual level 1 Data Flow Diagram Image**

Figure 7: BlueWaste’s Level 1 Context Diagram

The diagram highlights the flow of data such as waste report submissions, geolocation coordinates, photo uploads, status updates, and assignments between the system and its external stakeholders. It provides a high-level view of how the system collects, processes, and delivers information to support effective waste reporting and cleanup coordination.


# Next section

# System Design
The system design phase focuses on transforming the analyzed requirements into a structured blueprint for the development of the BlueWaste system. The system is designed as a cross-platform application that follows a three-tier client-server architecture, where users interact through a web browser or mobile device while the server handles data processing and storage. It integrates geolocation services for coordinate capture, Cloudinary for media management, and a YOLO-based inference API for waste image analysis.
The system interface is designed as a role-based dashboard that presents information through maps, heatmaps, charts, and report management panels, allowing administrators and LGU workers to efficiently coordinate waste response activities. Citizens access a simplified reporting interface through the web or mobile platform. The design ensures scalability and reliability by supporting concurrent user sessions and continuous operation. Overall, the system design provides a comprehensive structure that enables efficient waste reporting, monitoring, and cleanup management.


# Next section 

# Entity Relationship Diagram (ERD)

The Entity-Relationship Diagram (ERD) illustrates the structure of the database for the BlueWaste system, showing the relationships between key entities involved in waste report management, as shown in Figure 9. The main entities include User, Report, Barangay, ResortArea, ReportImage, StatusHistory, Notification, ActivityLog, and WasteReport.


**Actual ERD Diagram (attached image)**

The User entity manages system access and is associated with roles such as Citizen, LGU Admin, Resort Admin, and LGU Worker. The Report entity serves as the central component, storing detailed information including waste category, priority level, geolocation coordinates, image analysis results, and lifecycle status. Reports are linked to Barangay and ResortArea entities for geographic coverage and assignment purposes. Supporting entities such as StatusHistory, Notification, ActivityLog, and ReportImage capture the operational lifecycle of each report, enabling transparent tracking and audit of all system activities.


# Next Section

# JSON Schema Diagram
JSON Schema is a vocabulary used to annotate and validate JSON documents. It defines how a JSON object should be structured, making it straightforward to ensure that data is formatted correctly across all system components. In the BlueWaste system, JSON Schema specifications govern all request and response payloads transmitted through the RESTful API endpoints, supporting automated validation and ensuring consistent data integrity across the web portal, mobile application, and backend services.

The JSON Schema for BlueWaste defines the structure of the primary data objects exchanged between the client applications and the server: waste report submissions, user account records, image analysis results, status lifecycle updates, and notification payloads. Each schema specifies the required fields, data types, value constraints, and enumeration rules for its corresponding object. As shown in Figure 10, the JSON Schema Diagram illustrates the structural hierarchy and constraints of the core BlueWaste data objects.
 


**Actual JSON SCHEMA Diagram (attached image)**

Figure 10: BlueWaste’s JSON Schema Diagram


This JSON Schema diagram establish a comprehensive and enforceable contract for all data exchanged through the BlueWaste. By validating each payload against its corresponding schema before processing, the system ensures that only correctly structured data enters the application layer, reducing runtime errors, improving data quality, and facilitating automated testing across all system modules

# Next section

# Data Dictionary

The data dictionary defines the database tables, attributes, key types, and field-level descriptions used by BlueWaste. Table 2 shows the complete list of tables, while Table 2.1 through Table 2.9 provide the detailed data dictionary for each corresponding table.

Table 2. List of BlueWaste Database Tables
Table Name	    Description
User            Stores user account and profile information for citizens, administrators, and LGU workers.
Report	        Stores submitted waste incident reports and lifecycle status information.
ResortArea	    Stores LGU-defined coverage areas used for report assignment and filtering.
ReportImage	    Stores image metadata associated with submitted reports.
Barangay	    Stores barangay reference records and map coordinates.
StatusHistory	Stores report status transition logs and change notes.
Notification	Stores user notifications for assignments, updates, and system events.
ActivityLog	    Stores auditable user activity events and metadata.
WasteReport	    Stores waste detection records and related output labels.

Table 2.1 Data Dictionary for User
Attributes	Data Type	Key Type	Description
id	        UUID	PK	Unique identifier of the user.
email	    VARCHAR	UK	Login email address.
password	VARCHAR	-	Hashed password credential.
firstName	VARCHAR	-	User given name.
lastName	VARCHAR	-	User family name.
phone	    VARCHAR	-	Optional contact number.
role	    ENUM	-	User role (CITIZEN, LGU_ADMIN, RESORT_ADMIN, FIELD_WORKER).
avatarUrl	VARCHAR	-	Optional profile image URL.
isActive	BOOLEAN	-	Account active status flag.
createdAt	TIMESTAMP	-	Date and time when account was created.
updatedAt	TIMESTAMP	-	Date and time when account was last updated.
barangayId	UUID	FK	References Barangay.id for user location context.


Table 2.2 Data Dictionary for Report
Attributes	        Data Type	Key Type	Description
id	                UUID	PK	Unique identifier of the report.
title	            VARCHAR	-	Report title.
description	        TEXT	-	Detailed waste incident description.
category	        ENUM	-	Waste category classification.
status	            ENUM	-	Current report lifecycle status.
priority	        ENUM	-	Assigned urgency level.
latitude	        DOUBLE	-	Latitude coordinate of incident.
longitude	        DOUBLE	-	Longitude coordinate of incident.
address	            VARCHAR	-	Optional textual incident address.
isAnonymous 	    BOOLEAN	-	Indicates anonymous submission.
isDeleted	        BOOLEAN	-	Soft-delete marker.
isSpam	            BOOLEAN	-	Spam classification marker.
spamMarkedAt	    TIMESTAMP	-	Date and time report was marked as spam.
spamReason	        VARCHAR	-	Reason for spam classification.
analysisStatus	    ENUM	-	Image analysis decision status.
analysisWasteCount	INTEGER	-	Number of detected waste objects.
analysisConfidence	DOUBLE	-	Confidence value from the analysis.
analyzedAt	        TIMESTAMP	-	Date and time of analysis completion.
createdAt	        TIMESTAMP	-	Date and time report was created.
updatedAt	        TIMESTAMP	-	Date and time report was last updated.
reporterId	        UUID	FK	References User.id of reporting user.
assignedToId	    UUID	FK	References User.id of assigned LGU worker.
barangayId	        UUID	FK	References Barangay.id of report location.
resortAreaId	    UUID	FK	References ResortArea.id of mapped service area.


# I Won't be putting all their table because i want you to just know that this is their work and how it should be this section done

# Next section

# Technologies, Concepts, and Theories

This section discusses the model and process flow of the **BlueWaste** system, followed by the specific technologies and frameworks required for its development.

---

## The System Model and Process Flow

The system follows a structured data processing model to ensure accurate waste incident capture, analysis, and geospatial reporting.

### Report Submission

Citizens submit waste incident reports through the web or mobile platform by capturing a geolocation coordinate pair and uploading one or more photo images. The submission payload includes a title, description, waste category, and optional address field.

### Image Analysis

Upon report submission, the uploaded images are forwarded to a YOLO-based inference API. The API returns detected object labels, waste type classification, waste count, and a confidence score. These values are stored alongside the report record and used to assess report validity and prioritize response.

### Report Processing and Assignment

The application layer validates the incoming report, stores structured data in PostgreSQL, and links media assets through Cloudinary. LGU administrators review validated reports through the administrative dashboard, assign priority levels, and dispatch LGU workers for cleanup operations.

### Status Lifecycle Management

Reports pass through defined status stages including submission, assignment, in-progress cleanup, and resolution. Each status transition is recorded in the `StatusHistory` table with a timestamp and optional notes, providing a complete audit trail for every report.

### Geospatial Visualization

Stored report coordinates are consumed by mapping services on the web platform to render incident markers, coverage heatmaps, and barangay-level analytics charts that support data-driven cleanup prioritization.

---

# Technical Stack and Utilization

**Table 3. Technical Stack and Utilization of BlueWaste**

| Technology | Definition | Utilization |
|---|---|---|
| **Next.js with Tailwind CSS** | A React-based web framework with utility-first CSS styling support through Tailwind CSS. | Built the web application interfaces for citizens and administrators, including maps, report views, and dashboard pages. |
| **Node.js and Express** | A JavaScript runtime and minimal web framework for building server-side applications. | Used as the primary backend to handle RESTful API endpoints, business logic, authentication, and service integration. |
| **Flutter** | A cross-platform UI framework for building natively compiled mobile applications from a single codebase. | Used to develop the citizen web portal, administrative dashboard, and the cross-platform mobile application for field operations. |
| **PostgreSQL** | An open-source object-relational database management system. | Used as the centralized database to store user accounts, waste reports, geolocation data, status histories, notifications, and analytics records. |
| **Prisma ORM** | A next-generation ORM for Node.js that simplifies database access with a type-safe query builder. | Used to define the database schema, manage migrations, and perform structured queries against the PostgreSQL database. |
| **Cloudinary** | A cloud-based media management platform for storing, transforming, and delivering images and videos. | Used to upload, store, and serve report images and cleanup documentation submitted by citizens and LGU workers. |
| **YOLO Inference API** | An object detection model (You Only Look Once) used to identify and classify objects in images. | Used to analyze submitted report images, detect waste objects, classify waste types, and return confidence scores for report validation. |
| **Leaflet / Google Maps API** | Open-source and commercial JavaScript libraries for interactive map rendering. | Used to display geotagged incident markers, coverage heatmaps, and barangay boundary overlays on the administrative and citizen map interfaces. |

# System Testing and Implementation

This section details the proposed validation and deployment strategy for **BlueWaste**.


# Next section
---  

## System Test Plan

The proponents will perform systematic testing across all system modules to ensure correctness, stability, and usability. Performance will be measured using the following metrics:

### Report Submission Accuracy

Verification that all submitted form fields, geolocation data, and image attachments are correctly captured and stored in the database without data loss.

### Analysis Reliability

Assessment of the YOLO inference API's ability to correctly detect waste objects and return consistent confidence scores across varied image inputs.

### Role-Based Access Control

Confirmation that each user role can only access and perform the operations permitted by their assigned access level.

### Map Rendering Accuracy

Validation that geotagged report coordinates are correctly rendered on the interactive map, and that heatmap layers accurately reflect report density across coverage areas.

---

# Summary of Proposed Testing Findings

**Table 4. Summary of Proposed Testing Findings**

| Test Case | Performance Metric | Expected Result |
|---|---|---|
| **Report Submission** | Data Completeness | > 98% of reports stored with complete field data and media links. |
| **Image Analysis** | Detection Reliability | Waste objects correctly detected in at least 85% of submitted images. |
| **Role-Based Access** | Access Control Accuracy | Unauthorized role operations blocked in 100% of test cases. |
| **Map Rendering** | Geolocation Precision | Report markers rendered within 10 meters of submitted coordinates. |

# Next section


# System Implementation Plan

The implementation will follow a phased approach aligned with the **Iterative Model**.

---

## Preparation Phase

The development environment will be configured, backend API services will be set up on a cloud hosting platform, and database schemas will be initialized through Prisma migrations. Cloudinary and YOLO API integrations will be validated before the first iteration deployment.

## Iterative Development and Testing

Each iteration will deliver a functional increment of the system, beginning with core report submission and user authentication, followed by report management and assignment features, and culminating in the analysis, mapping, and analytics modules. Each increment will be tested before the next iteration begins.

## Deployment and Evaluation

The completed system will be deployed for access by target users including LGU administrators and citizens. A usability evaluation will be conducted using a standardized instrument to measure the system's effectiveness, efficiency, and user satisfaction in supporting waste monitoring operations.

---

# Next Section

# System Maintenance

As the project progresses and the system is deployed, the following plans will be enacted to ensure the longevity, security, and continued effectiveness of **BlueWaste**.

---

# Systems Security Plan

To protect the integrity of waste report data and user information, the following security measures will be implemented:

## Authentication and Authorization

A secure role-based authentication system will be implemented using JSON Web Tokens (JWT) [23]. Distinct access levels for Citizen, LGU Worker, Resort Administrator, and LGU Administrator roles will enforce permission boundaries and prevent unauthorized data access or manipulation.

## Secure Media Handling

All image uploads will be routed through Cloudinary with signed upload credentials to prevent direct unauthorized file submission. Stored media URLs will be validated before retrieval.

## API Security

RESTful API endpoints will be protected through token-based middleware. Rate limiting will be applied to public-facing endpoints to mitigate abuse or denial-of-service attempts.

# Next Section

# Systems Maintenance Plan

To keep the system operational and up-to-date, the following activities will be performed:

---

## Database Archiving

A routine process will be scheduled to archive resolved report records and activity logs older than twelve months to maintain database performance and storage efficiency.

## Dependency Updates

All Node.js packages, Prisma ORM, and integrated service SDKs will be reviewed and updated on a regular basis to patch security vulnerabilities and maintain compatibility with evolving platform APIs.

## Model Refinement

As the YOLO inference API is used in production, detection results will be reviewed periodically to assess accuracy. If performance degrades, the model will be retrained or replaced with an updated version to maintain reliable waste classification.

## Feature Iteration

Feedback gathered from LGU administrators, LGU workers, and citizens during the evaluation phase will be incorporated into subsequent system iterations to improve usability, expand coverage, and address identified limitations.
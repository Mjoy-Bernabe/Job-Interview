-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Aug 05, 2026 at 01:29 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `auth_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `applicants`
--

CREATE TABLE `applicants` (
  `applicant_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `first_name` varchar(60) NOT NULL,
  `middle_initial` varchar(10) DEFAULT NULL,
  `last_name` varchar(60) NOT NULL,
  `full_name` varchar(140) GENERATED ALWAYS AS (trim(concat(`first_name`,' ',coalesce(concat(`middle_initial`,'. '),''),`last_name`))) STORED,
  `date_of_birth` date NOT NULL,
  `civil_status` enum('Single','Married','Widowed','Separated','Divorced') DEFAULT NULL,
  `gender` enum('Male','Female','Other','Prefer not to say') DEFAULT NULL,
  `current_location` varchar(100) NOT NULL,
  `preferred_location` varchar(100) DEFAULT NULL,
  `nationality` varchar(50) DEFAULT NULL,
  `phone_number` varchar(20) DEFAULT NULL,
  `linkedin_url` varchar(255) DEFAULT NULL,
  `portfolio_url` varchar(255) DEFAULT NULL,
  `resume_url` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `applicants`
--

INSERT INTO `applicants` (`applicant_id`, `user_id`, `first_name`, `middle_initial`, `last_name`, `date_of_birth`, `civil_status`, `gender`, `current_location`, `preferred_location`, `nationality`, `phone_number`, `linkedin_url`, `portfolio_url`, `resume_url`) VALUES
(1, 2, 'CRYSTAL', 'K', 'ILAO', '2000-08-09', NULL, NULL, '0970-828-1843 | ilaocrystal09@gmail.com | Makati City, Philippines | linkedin.com/in/crystal-kaye-il', 'ed throughout the SDLC.', NULL, NULL, NULL, NULL, 'D:\\xampp\\htdocs\\Simulation\\Job-Interview\\uploads\\53edd733ac1c42998a2379c850c9f137.docx'),
(7, 3, 'Jane', NULL, 'Smith', '1997-11-05', NULL, NULL, 'Makati City', NULL, NULL, NULL, NULL, NULL, 'static/uploads/resume_jane_smith.pdf'),
(8, 4, 'Alex', NULL, 'Jones', '1995-02-14', NULL, NULL, 'Mandaluyong City', NULL, NULL, NULL, NULL, NULL, 'static/uploads/resume_alex_jones.pdf'),
(9, 5, 'Bob', NULL, 'Wilson', '2000-01-20', NULL, NULL, 'Taguig City', NULL, NULL, NULL, NULL, NULL, 'static/uploads/resume_bob_wilson.pdf');

-- --------------------------------------------------------

--
-- Table structure for table `applicant_skills`
--

CREATE TABLE `applicant_skills` (
  `applicant_id` int(11) NOT NULL,
  `skill_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `applicant_skills`
--

INSERT INTO `applicant_skills` (`applicant_id`, `skill_id`) VALUES
(1, 15),
(1, 43);

-- --------------------------------------------------------

--
-- Table structure for table `applications`
--

CREATE TABLE `applications` (
  `application_id` int(11) NOT NULL,
  `job_id` int(11) NOT NULL,
  `applicant_id` int(11) NOT NULL,
  `resume_experience_years` decimal(5,1) DEFAULT NULL,
  `pre_screen_status` varchar(50) NOT NULL DEFAULT 'Pending',
  `chatbot_status` varchar(50) NOT NULL DEFAULT 'Pending',
  `applied_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `shortlisted` tinyint(1) NOT NULL DEFAULT 0,
  `interview_result` varchar(100) DEFAULT NULL,
  `final_interview_status` varchar(100) DEFAULT NULL,
  `final_interview_date` date DEFAULT NULL,
  `final_interviewer` varchar(100) DEFAULT NULL,
  `virtual_interview_status` varchar(100) DEFAULT NULL,
  `transcript_status` varchar(100) DEFAULT NULL,
  `interview_type` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `applications`
--

INSERT INTO `applications` (`application_id`, `job_id`, `applicant_id`, `resume_experience_years`, `pre_screen_status`, `chatbot_status`, `applied_at`, `shortlisted`, `interview_result`, `final_interview_status`, `final_interview_date`, `final_interviewer`, `virtual_interview_status`, `transcript_status`, `interview_type`) VALUES
(24, 3, 1, 3.5, 'Passed Screening', 'Pending', '2026-07-14 19:48:51', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
(25, 1, 1, 3.5, 'Passed Screening', 'Pending', '2026-07-14 19:58:14', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
(36, 5, 1, 2.0, 'Failed Screening', 'Pending', '2026-07-16 08:52:10', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `application_overall_status`
--

CREATE TABLE `application_overall_status` (
  `overall_id` int(11) NOT NULL,
  `application_id` int(11) NOT NULL,
  `pre_screen_snapshot` varchar(50) NOT NULL,
  `chatbot_snapshot` varchar(50) DEFAULT NULL,
  `overall_status` varchar(50) NOT NULL DEFAULT 'Pending',
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `application_overall_status`
--

INSERT INTO `application_overall_status` (`overall_id`, `application_id`, `pre_screen_snapshot`, `chatbot_snapshot`, `overall_status`, `updated_at`) VALUES
(3, 24, 'Passed Screening', 'Not Qualified', 'Rejected', '2026-07-14 19:57:23'),
(18, 36, 'Failed Screening', NULL, 'Rejected', '2026-07-16 08:52:10');

-- --------------------------------------------------------

--
-- Table structure for table `chatbot`
--

CREATE TABLE `chatbot` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `application_id` int(11) DEFAULT NULL,
  `user_name` varchar(255) NOT NULL,
  `position` varchar(100) DEFAULT NULL,
  `experience` int(11) DEFAULT NULL,
  `skills` text DEFAULT NULL,
  `qualification_status` varchar(50) DEFAULT NULL,
  `advice` text DEFAULT NULL,
  `assessment_data` longtext DEFAULT NULL CHECK (json_valid(`assessment_data`)),
  `confidence` float DEFAULT NULL,
  `average_score` float DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `chatbot`
--

INSERT INTO `chatbot` (`id`, `user_id`, `application_id`, `user_name`, `position`, `experience`, `skills`, `qualification_status`, `advice`, `assessment_data`, `confidence`, `average_score`, `created_at`) VALUES
(0, 2, NULL, 'MARYJOY', 'Business Analyst', 0, '[]', 'Not Qualified', '[{\"question\": \"Tell me about yourself.\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"Why are you leaving your current job?\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"How do you handle criticism?\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"Why should we hire you?\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"Tell me about a time you had to solve a difficult problem at work.\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"Give an example of a time you supported a teammate under pressure.\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"Have you ever taken the lead on a project? What happened?\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"Give an example of a mistake you made and how you handled it.\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"How do you prioritize tasks when handling multiple small projects?\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"How do you handle conflicts between team members?\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"What is the difference between a project and a program in IT?\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"How do you stay organized when working on multiple deliverables?\", \"suggestion\": \"Well answered, keep it up.\"}]', '[{\"question\": \"Tell me about yourself.\", \"answer\": \"My name is Maryjoy, and I\\u2019m applying for the Business Analyst role. I have a strong background in analyzing business processes, gathering requirements, and translating them into actionable solutions that improve efficiency and support organizational goals. Over the past few years, I\\u2019ve built expertise in data analysis, documentation, and stakeholder communication, which has helped me bridge the gap between technical teams and business needs. I\\u2019m motivated by opportunities to identify problems, propose practical solutions, and contribute to projects that drive measurable impact. Outside of work, I enjoy continuous learning\\u2014whether it\\u2019s exploring new tools for data visualization or keeping up with industry trends\\u2014because I believe adaptability is key in today\\u2019s fast-changing business environment.\", \"qualificationStatus\": \"Not Qualified\"}, {\"question\": \"Why are you leaving your current job?\", \"answer\": \"I\\u2019ve really valued the experience and skills I gained in my current role, especially working on projects that improved efficiency and strengthened collaboration between teams. However, I feel I\\u2019ve reached a point where growth opportunities are limited, and I\\u2019m eager to take on new challenges that will allow me to expand my expertise further. I\\u2019m particularly excited about the chance to contribute to a company where I can apply my analytical skills to drive meaningful business improvements and continue developing professionally.\", \"qualificationStatus\": \"Not Qualified\"}, {\"question\": \"How do you handle criticism?\", \"answer\": \"I see criticism as an opportunity to improve, especially when it\'s constructive. I listen carefully without taking it personally, ask questions if I need clarification, and identify what I can do better. For example, if a stakeholder or supervisor points out that my requirements document lacks detail or clarity, I would review their feedback, make the necessary revisions, and ensure I avoid the same issue in future projects. I believe being open to feedback helps me grow professionally and work more effectively with my team.\", \"qualificationStatus\": \"Qualified\"}, {\"question\": \"Why should we hire you?\", \"answer\": \"You should hire me because I have a strong willingness to learn, good analytical and problem-solving skills, and I communicate well with others. As a Computer Science student, I\'ve worked on projects that involved gathering requirements, analyzing data, and proposing solutions to real-world problems. I enjoy understanding business needs and translating them into practical solutions. I\'m also adaptable, detail-oriented, and committed to continuous improvement. While I\'m still early in my career, I\'m eager to contribute, learn from experienced professionals, and add value to your team\", \"qualificationStatus\": \"Qualified\"}, {\"question\": \"Tell me about a time you had to solve a difficult problem at work.\", \"answer\": \"\\\"One difficult problem I faced was during our capstone project, where we were developing an AI-assisted recruitment system. We encountered an issue with our resume screening feature because the system produced inconsistent results for resumes with the same content but in different file formats, such as PDF and DOCX. I analyzed the root cause, researched different text extraction methods, and worked with my team to improve the preprocessing and extraction process so the screening became more consistent. Throughout the process, we tested different solutions, gathered feedback, and refined the system until we achieved better accuracy. This experience taught me the importance of critical thinking, collaboration, and continuously improving a solution based on testing and feedback.\", \"qualificationStatus\": \"Not Qualified\"}, {\"question\": \"Give an example of a time you supported a teammate under pressure.\", \"answer\": \"During our capstone project, one of my teammates was overwhelmed with multiple tasks and was struggling to meet our deadline. To support the team, I offered to help by reviewing their work, assisting with documentation, and testing parts of the system so they could focus on the more complex development tasks. We also communicated regularly to prioritize the most important features and divide the workload effectively. Because we worked together and supported one another, we completed the project on time and delivered a functional system. This experience reinforced the importance of teamwork, communication, and staying calm under pressure.\", \"qualificationStatus\": \"Not Qualified\"}, {\"question\": \"Have you ever taken the lead on a project? What happened?\", \"answer\": \"Yes. During our capstone project, I took the lead in coordinating parts of our AI-assisted recruitment system. I helped gather and organize the project requirements, assigned tasks based on each team member\'s strengths, monitored our progress, and made sure everyone stayed aligned with our timeline. I also communicated with our adviser to clarify feedback and ensured that our team incorporated the necessary improvements. Although there were challenges, such as changing requirements and technical issues, we worked together, adapted our plans, and successfully completed the project. That experience strengthened my leadership, communication, and project management skills.\", \"qualificationStatus\": \"Not Qualified\"}, {\"question\": \"Give an example of a mistake you made and how you handled it.\", \"answer\": \"During our capstone project, I initially underestimated the time needed to integrate and test one of our system features. Because of that, we experienced delays in our development schedule. I took responsibility for the mistake, informed my teammates immediately, and worked with them to adjust our timeline and prioritize the most critical tasks. I also created a more detailed task schedule and monitored our progress more closely to prevent similar delays. In the end, we completed the project successfully. That experience taught me the importance of realistic planning, proactive communication, and managing risks early.\", \"qualificationStatus\": \"Not Qualified\"}, {\"question\": \"How do you prioritize tasks when handling multiple small projects?\", \"answer\": \"When I have multiple tasks or small projects, I first identify which ones are the most urgent and have the greatest impact. I break larger tasks into smaller, manageable steps, set deadlines, and use a task list or project management tool to stay organized. If priorities change, I communicate with my team or supervisor to make sure I\'m focusing on the right tasks. I also review my progress regularly to ensure everything stays on track. This approach helps me manage my workload efficiently while maintaining the quality of my work.\", \"qualificationStatus\": \"Qualified\"}, {\"question\": \"How do you handle conflicts between team members?\", \"answer\": \"When conflicts arise between team members, I try to remain neutral and understand each person\'s perspective before making any assumptions. I encourage open and respectful communication so everyone has the opportunity to express their concerns. Then, I focus on finding a solution that supports the team\'s goals rather than individual preferences. If the conflict cannot be resolved through discussion, I would involve the appropriate team lead or supervisor. I believe addressing conflicts professionally and early helps maintain a positive working environment and keeps the project moving forward.\", \"qualificationStatus\": \"Qualified\"}, {\"question\": \"What is the difference between a project and a program in IT?\", \"answer\": \"A project is a temporary effort with a specific goal, timeline, and deliverable, such as developing a new mobile application or implementing a new feature. A program, on the other hand, is a group of related projects that are managed together to achieve a broader business objective. While a project focuses on delivering a specific outcome, a program focuses on coordinating multiple projects to maximize overall business value and ensure they align with the organization\'s strategic goals.\", \"qualificationStatus\": \"Qualified\"}, {\"question\": \"How do you stay organized when working on multiple deliverables?\", \"answer\": \"I stay organized by planning my tasks at the beginning of each day or week and prioritizing them based on deadlines and business impact. I break large deliverables into smaller, manageable tasks and track my progress using tools like task lists, spreadsheets, or project management software. I also review my priorities regularly and communicate with my team if timelines or requirements change. Staying organized helps me meet deadlines while maintaining the quality of my work.\", \"qualificationStatus\": \"Qualified\"}]', 50, 0.5, '2026-07-14 13:01:25'),
(0, 2, NULL, 'MARYJOY', 'Project Analyst', 3, '[]', 'Qualified', '[{\"question\": \"How do you prioritize tasks when handling multiple small projects?\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"How do you handle conflicts between team members?\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"What is the difference between a project and a program in IT?\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"How do you stay organized when working on multiple deliverables?\", \"suggestion\": \"Review this topic to improve your knowledge.\"}]', '[{\"question\": \"How do you prioritize tasks when handling multiple small projects?\", \"answer\": \"I prioritize tasks by evaluating their urgency, business impact, and deadlines. I break each project into manageable tasks, identify dependencies, and focus on high-priority activities first. I also use planning tools to track progress, communicate regularly with stakeholders, and adjust priorities when project requirements change to ensure all projects are completed efficiently and on time.\", \"score\": 0.76, \"cosine_score\": 0.82, \"keyword_score\": 0.6, \"qualificationStatus\": \"Qualified\"}, {\"question\": \"How do you handle conflicts between team members?\", \"answer\": \"I handle conflicts by listening to each team member\'s perspective, identifying the root cause of the issue, and encouraging open and respectful communication. I focus on finding a solution that supports the project\'s goals while maintaining positive working relationships. If needed, I involve the appropriate stakeholders to ensure the conflict is resolved fairly and professionally.\", \"score\": 0.68, \"cosine_score\": 0.71, \"keyword_score\": 0.6, \"qualificationStatus\": \"Partially Qualified\"}, {\"question\": \"What is the difference between a project and a program in IT?\", \"answer\": \"A project is a temporary effort with a defined scope, timeline, and objectives to deliver a specific product, service, or result. In contrast, a program is a collection of related projects managed together to achieve broader strategic goals and deliver greater organizational value. While projects focus on specific deliverables, programs focus on long-term business outcomes and coordination across multiple projects.\", \"score\": 0.67, \"cosine_score\": 0.79, \"keyword_score\": 0.4, \"qualificationStatus\": \"Partially Qualified\"}, {\"question\": \"How do you stay organized when working on multiple deliverables?\", \"answer\": \"I stay organized by creating a clear project plan, prioritizing tasks based on deadlines and business impact, and tracking progress using project management tools. I break deliverables into smaller, manageable tasks, maintain regular communication with the team, and review priorities frequently to ensure deadlines are met and project objectives are achieved efficiently.\", \"score\": 0.56, \"cosine_score\": 0.63, \"keyword_score\": 0.4, \"qualificationStatus\": \"Partially Qualified\"}]', 25, 0.6675, '2026-07-14 17:17:39'),
(0, 2, 24, 'MARYJOY', 'Java Developer', 4, '[]', 'Not Qualified', '[{\"question\": \"What are the main principles of OOP and how does Java implement them?\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"Explain the differences between ArrayList, LinkedList, and HashMap.\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"How does garbage collection work in Java?\", \"suggestion\": \"Review this topic to improve your knowledge.\"}, {\"question\": \"Explain how you would connect a Java application to a database (JDBC or ORM).\", \"suggestion\": \"Review this topic to improve your knowledge.\"}]', '[{\"question\": \"What are the main principles of OOP and how does Java implement them?\", \"answer\": \"I understand that multi-threading in Java allows a program to run multiple tasks at the same time, which improves performance and responsiveness. I manage multi-threading by creating threads using the Thread class or implementing the Runnable interface. In modern Java, I also know that ExecutorService is recommended because it manages thread pools efficiently.  For example, if I were developing a file upload system, one thread could handle uploading files while another updates the user interface, so the application doesn\'t freeze. Another example is a chat application where one thread listens for incoming messages while another sends messages. Although I haven\'t worked on large production systems yet, I\'ve studied these concepts in Java and understand when and why multi-threading is used\", \"score\": 0.3, \"qualification_status\": \"Not Qualified\", \"feedback\": \"Answer lacks relevance. Try to address the question more directly.\", \"matched_keywords\": [\"java\"], \"missing_keywords\": [\"java implement\", \"principles oop\", \"does java\", \"oop\"], \"total_keywords\": [\"java implement\", \"principles oop\", \"java\", \"does java\", \"oop\"], \"cosine_score\": 0.35, \"keyword_score\": 0.2}, {\"question\": \"Explain the differences between ArrayList, LinkedList, and HashMap.\", \"answer\": \"While I haven\'t formally mentored junior developers in a professional setting, I have helped classmates during group projects and programming activities. When someone had difficulty understanding Java concepts, I explained them step by step using simple examples and encouraged them to practice by writing small programs on their own.  I also reviewed their code, pointed out errors, and suggested improvements based on Java best practices, such as using meaningful variable names and organizing code into methods. I believe the best way to help someone improve is to be patient, encourage questions, and provide constructive feedback. This approach helped our team complete projects more efficiently while allowing everyone to strengthen their programming skills.\", \"score\": 0.11, \"qualification_status\": \"Not Qualified\", \"feedback\": \"Answer lacks relevance. Try to address the question more directly.\", \"matched_keywords\": [], \"missing_keywords\": [\"linkedlist hashmap\", \"arraylist linkedlist\", \"differences arraylist\", \"arraylist\", \"linkedlist\"], \"total_keywords\": [\"linkedlist hashmap\", \"arraylist linkedlist\", \"differences arraylist\", \"arraylist\", \"linkedlist\"], \"cosine_score\": 0.16, \"keyword_score\": 0.0}, {\"question\": \"How does garbage collection work in Java?\", \"answer\": \"When designing a scalable Java application, I would start by creating a modular architecture where each component has a clear responsibility. I would separate the user interface, business logic, and database layers to make the application easier to maintain and expand. I would also write clean, reusable code, optimize database queries, and use connection pooling and caching when appropriate to improve performance.  Some challenges I would anticipate include handling a large number of users, maintaining application performance, and ensuring data consistency. To address these, I would optimize the code, use efficient data structures, implement proper exception handling and logging, and perform regular testing to identify performance bottlenecks. As the application grows, I would also consider using frameworks like Spring Boot and, if needed, breaking the application into smaller services to improve scalability. Although I haven\'t built a large-scale production system yet, I understand these principles and I\'m eager to apply them in real-world projects.\", \"score\": 0.2, \"qualification_status\": \"Not Qualified\", \"feedback\": \"Answer lacks relevance. Try to address the question more directly.\", \"matched_keywords\": [\"java\"], \"missing_keywords\": [\"garbage collection\", \"does garbage\", \"garbage\", \"work java\"], \"total_keywords\": [\"garbage collection\", \"does garbage\", \"garbage\", \"java\", \"work java\"], \"cosine_score\": 0.2, \"keyword_score\": 0.2}, {\"question\": \"Explain how you would connect a Java application to a database (JDBC or ORM).\", \"answer\": \"Both synchronized methods and synchronized blocks are used in Java to prevent multiple threads from accessing shared resources at the same time, helping to avoid race conditions.  The main difference is that a synchronized method locks the entire method, so only one thread can execute that method for a given object at a time. A synchronized block, however, locks only a specific section of code and allows me to choose which object to lock. This makes synchronized blocks more flexible and can improve performance because only the critical code is locked instead of the whole method.  In general, I would use a synchronized method when the entire method needs thread safety, and a synchronized block when only part of the method accesses shared data and I want to minimize the time the lock is held.\", \"score\": 0.14, \"qualification_status\": \"Not Qualified\", \"feedback\": \"Answer lacks relevance. Try to address the question more directly.\", \"matched_keywords\": [], \"missing_keywords\": [\"jdbc orm\", \"database jdbc\", \"jdbc\", \"java application\", \"connect java\"], \"total_keywords\": [\"jdbc orm\", \"database jdbc\", \"jdbc\", \"java application\", \"connect java\"], \"cosine_score\": 0.2, \"keyword_score\": 0.0}]', 0, 0.19, '2026-07-14 19:57:22'),
(0, 2, 25, 'MARYJOY', 'PHP Developer', 4, '[]', 'Qualified', '[{\"question\": \"What are the main principles of OOP and how does Java implement them?\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"Explain the differences between ArrayList, LinkedList, and HashMap.\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"How does garbage collection work in Java?\", \"suggestion\": \"Well answered, keep it up.\"}, {\"question\": \"Explain how you would connect a Java application to a database (JDBC or ORM).\", \"suggestion\": \"Well answered, keep it up.\"}]', '[{\"question\": \"What are the main principles of OOP and how does Java implement them?\", \"answer\": \"The main principles of OOP are encapsulation, inheritance, polymorphism, and abstraction. Java implements these by using classes, access modifiers, getters and setters for encapsulation, the extends keyword for inheritance, method overloading and overriding for polymorphism, and abstract classes or interfaces for abstraction, making programs more reusable, organized, and easier to maintain.\", \"score\": 0.77, \"qualification_status\": \"Qualified\", \"feedback\": \"Good answer with relevant content.\", \"matched_keywords\": [\"java implement\", \"java\", \"oop\"], \"missing_keywords\": [\"principles oop\", \"does java\"], \"total_keywords\": [\"java implement\", \"principles oop\", \"java\", \"does java\", \"oop\"], \"cosine_score\": 0.84, \"keyword_score\": 0.6}, {\"question\": \"Explain the differences between ArrayList, LinkedList, and HashMap.\", \"answer\": \"ArrayList, LinkedList, and HashMap are Java collection classes with different purposes. ArrayList stores elements in a dynamic array and provides fast access using indexes but can be slower when inserting or deleting elements in the middle. LinkedList stores elements as connected nodes, making insertion and deletion faster but slower for accessing elements by index. HashMap stores data as key-value pairs and provides fast lookup using unique keys, making it useful for retrieving values efficiently.\", \"score\": 0.78, \"qualification_status\": \"Qualified\", \"feedback\": \"Good answer with relevant content.\", \"matched_keywords\": [\"arraylist linkedlist\", \"arraylist\", \"linkedlist\"], \"missing_keywords\": [\"linkedlist hashmap\", \"differences arraylist\"], \"total_keywords\": [\"linkedlist hashmap\", \"arraylist linkedlist\", \"differences arraylist\", \"arraylist\", \"linkedlist\"], \"cosine_score\": 0.85, \"keyword_score\": 0.6}, {\"question\": \"How does garbage collection work in Java?\", \"answer\": \"Garbage collection in Java automatically manages memory by identifying and removing objects that are no longer being used or referenced by a program. The Java Virtual Machine (JVM) uses a garbage collector to free up memory from unused objects, helping prevent memory leaks and improving application performance without requiring developers to manually release memory.\", \"score\": 0.77, \"qualification_status\": \"Qualified\", \"feedback\": \"Good answer with relevant content.\", \"matched_keywords\": [\"garbage collection\", \"garbage\", \"java\"], \"missing_keywords\": [\"does garbage\", \"work java\"], \"total_keywords\": [\"garbage collection\", \"does garbage\", \"garbage\", \"java\", \"work java\"], \"cosine_score\": 0.84, \"keyword_score\": 0.6}, {\"question\": \"Explain how you would connect a Java application to a database (JDBC or ORM).\", \"answer\": \"To connect a Java application to a database, I can use JDBC by loading the database driver, creating a connection using the database URL, username, and password, then executing SQL queries through statements or prepared statements and processing the results. Alternatively, I can use an ORM framework like Hibernate or JPA, which maps Java objects to database tables and allows developers to interact with the database using objects instead of writing SQL queries directly.\", \"score\": 0.7, \"qualification_status\": \"Qualified\", \"feedback\": \"Good answer with relevant content.\", \"matched_keywords\": [\"jdbc\", \"java application\"], \"missing_keywords\": [\"jdbc orm\", \"database jdbc\", \"connect java\"], \"total_keywords\": [\"jdbc orm\", \"database jdbc\", \"jdbc\", \"java application\", \"connect java\"], \"cosine_score\": 0.83, \"keyword_score\": 0.4}]', 100, 0.76, '2026-07-14 20:02:22');

-- --------------------------------------------------------

--
-- Table structure for table `chatbot_backup`
--

CREATE TABLE `chatbot_backup` (
  `id` int(11) NOT NULL DEFAULT 0,
  `user_name` varchar(100) NOT NULL,
  `position` varchar(255) DEFAULT NULL,
  `qualifications` text NOT NULL,
  `qualification_status` varchar(50) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `experience_years` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `chatbot_limits`
--

CREATE TABLE `chatbot_limits` (
  `id` int(11) NOT NULL,
  `position` varchar(100) NOT NULL,
  `max_allowed` int(11) NOT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `educations`
--

CREATE TABLE `educations` (
  `education_id` int(11) NOT NULL,
  `applicant_id` int(11) NOT NULL,
  `degree_level` varchar(100) NOT NULL,
  `major` varchar(100) NOT NULL,
  `institution` varchar(150) NOT NULL,
  `graduation_year` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `educations`
--

INSERT INTO `educations` (`education_id`, `applicant_id`, `degree_level`, `major`, `institution`, `graduation_year`) VALUES
(33, 1, 'Bachelor\'s', 'N/A', 'Innovative College of Science and Technology ICST | 2023', 2023);

-- --------------------------------------------------------

--
-- Table structure for table `jobs`
--

CREATE TABLE `jobs` (
  `job_id` int(11) NOT NULL,
  `job_name` varchar(100) NOT NULL,
  `max_applicants` int(11) NOT NULL,
  `application_status` varchar(20) NOT NULL DEFAULT 'Open' CHECK (`application_status` in ('Open','Closed','Paused')),
  `opening_date` date NOT NULL,
  `application_deadline` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `jobs`
--

INSERT INTO `jobs` (`job_id`, `job_name`, `max_applicants`, `application_status`, `opening_date`, `application_deadline`) VALUES
(1, 'PHP Developer', 50, 'Open', '2026-07-12', '2026-08-12'),
(3, 'Java Developer', 50, 'Open', '2026-07-14', '2026-08-13'),
(4, 'Business Analyst', 30, 'Open', '2026-07-17', '2026-07-17'),
(5, 'Project Analyst', 20, 'Open', '2026-07-16', '2026-07-16'),
(6, 'Software Developer', 5, 'Open', '2026-07-15', '2026-07-15');

-- --------------------------------------------------------

--
-- Table structure for table `job_desc`
--

CREATE TABLE `job_desc` (
  `job_desc_id` int(11) NOT NULL,
  `job_id` int(11) NOT NULL,
  `description` text NOT NULL,
  `department` varchar(100) NOT NULL,
  `employment_type` varchar(50) NOT NULL,
  `work_setup` enum('Onsite','Hybrid','Remote') DEFAULT NULL,
  `work_schedule` varchar(100) DEFAULT NULL,
  `location` varchar(100) NOT NULL,
  `salary_range` varchar(50) DEFAULT NULL,
  `vacancies` int(11) NOT NULL DEFAULT 1,
  `education_baseline` varchar(100) NOT NULL,
  `required_degree` varchar(100) DEFAULT NULL,
  `required_course` varchar(100) DEFAULT NULL,
  `required_exp_years` int(11) NOT NULL DEFAULT 0,
  `minimum_age` int(11) NOT NULL DEFAULT 18,
  `required_gender` enum('Male','Female','Any') NOT NULL DEFAULT 'Any',
  `required_civil_status` enum('Single','Married','Widowed','Separated','Divorced','Any') NOT NULL DEFAULT 'Any',
  `education_notes` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `job_desc`
--

INSERT INTO `job_desc` (`job_desc_id`, `job_id`, `description`, `department`, `employment_type`, `work_setup`, `work_schedule`, `location`, `salary_range`, `vacancies`, `education_baseline`, `required_degree`, `required_course`, `required_exp_years`, `minimum_age`, `required_gender`, `required_civil_status`, `education_notes`) VALUES
(1, 1, 'We are looking for a PHP Developer responsible for developing, testing, and maintaining web applications. The candidate should have experience in backend development, database management, and REST APIs.', 'Information Technology', 'Full-time', NULL, NULL, 'Pasig City, Metro Manila', '?30,000 - ?45,000', 3, 'Bachelor\'s Degree in Computer Science, Information Technology, or related field', NULL, NULL, 2, 21, 'Any', 'Any', 'Fresh graduates with strong portfolios may also apply.'),
(9, 3, 'Responsible for developing, maintaining, and deploying enterprise Java applications. Requires strong knowledge of Spring Boot, Hibernate, and RESTful APIs.', 'Information Technology', 'Full-time', NULL, NULL, 'Pasig City', 'PHP50,000 - PHP70,000', 3, 'Bachelor\'s Degree', NULL, NULL, 3, 18, 'Any', 'Any', NULL),
(10, 4, 'Not specified', 'Operations', 'Full-time', 'Onsite', NULL, 'Manila', 'PHP40,000 - PHP55,000', 4, 'Bachelor\'s Degree', NULL, NULL, 1, 18, 'Any', 'Any', ''),
(11, 5, 'Job Summary\r\n\r\nWe are seeking a detail-oriented and analytical Project Analyst to support project planning, execution, and monitoring. The Project Analyst will work closely with project managers and cross-functional teams to analyze project requirements, track progress, prepare reports, and ensure projects are completed on time, within scope, and within budget.\r\n\r\nKey Responsibilities\r\nAssist in planning, scheduling, and coordinating project activities.\r\nMonitor project progress and identify potential risks or delays.\r\nGather, organize, and analyze project data.\r\nPrepare project documentation, reports, and presentations.\r\nTrack project timelines, milestones, and deliverables.\r\nCoordinate with team members and stakeholders to ensure effective communication.\r\nSupport resource allocation and project budgeting activities.\r\nMaintain accurate project records and documentation.\r\nRecommend process improvements to increase project efficiency.\r\nPerform other project-related tasks as assigned.\r\nQualifications\r\nBachelor\'s degree in Information Technology, Computer Science, Business Administration, Industrial Engineering, or a related field.\r\nStrong analytical and problem-solving skills.\r\nExcellent written and verbal communication skills.\r\nProficient in Microsoft Office (Excel, Word, PowerPoint).\r\nFamiliarity with project management tools such as Jira, Trello, Asana, or Microsoft Project is an advantage.\r\nAbility to manage multiple tasks and meet deadlines.\r\nStrong organizational and time management skills.\r\nAbility to work independently and collaboratively within a team.\r\nPreferred Skills\r\nData analysis and reporting.\r\nProject planning and scheduling.\r\nRisk assessment and issue tracking.\r\nDocumentation and report writing.\r\nBasic knowledge of Agile or Scrum methodologies.\r\nCritical thinking and decision-making.\r\nAttention to detail.\r\nExperience\r\nFresh graduates are encouraged to apply.\r\nExperience in project coordination, business analysis, software development, or project management is an advantage.\r\nEmployment Type\r\nFull-Time\r\nWork Setup\r\nOn-site / Hybrid (depending on company policy)', 'PMO', 'Full-time', 'Onsite', NULL, 'Pasig City', 'PHP35,000 - PHP45,000', 5, 'Master\'s Degree', NULL, NULL, 1, 18, 'Any', 'Any', ''),
(12, 6, 'Position Overview:\r\nWe are seeking a Software Developer responsible for designing, developing, testing, and maintaining software applications. The ideal candidate should have strong programming skills, problem-solving abilities, and experience in building reliable and scalable software solutions.\r\n\r\nResponsibilities:\r\n\r\nDesign, develop, and maintain software applications based on business requirements.\r\nWrite clean, efficient, and maintainable code using programming languages such as Java, PHP, Python, C++, or JavaScript.\r\nAnalyze user requirements and translate them into technical solutions.\r\nPerform software testing, debugging, and troubleshooting to ensure application quality.\r\nCollaborate with developers, designers, QA testers, and stakeholders throughout the software development lifecycle.\r\nDevelop and maintain databases, APIs, and system integrations.\r\nOptimize application performance and improve existing software features.\r\nDocument technical specifications, code changes, and development processes.\r\nFollow software development best practices, coding standards, and Agile methodologies.\r\n\r\nQualifications:\r\n\r\nBachelor’s degree in Computer Science, Information Technology, Software Engineering, or a related field.\r\nExperience with software development and programming concepts.\r\nKnowledge of object-oriented programming (OOP), data structures, and algorithms.\r\nFamiliarity with databases such as MySQL, PostgreSQL, or SQL Server.\r\nExperience with version control systems such as Git.\r\nUnderstanding of web development frameworks and software architecture is an advantage.\r\nStrong analytical and problem-solving skills.\r\nAbility to work independently and collaborate with a development team.\r\n\r\nRequired Skills:\r\n\r\nProgramming languages: Java, PHP, Python, C++, JavaScript\r\nFront-end technologies: HTML, CSS, JavaScript\r\nBack-end development and API integration\r\nDatabase management and SQL\r\nDebugging and software testing\r\nVersion control using Git\r\nAgile/Scrum development practices\r\n\r\nPreferred Experience:\r\n\r\nExperience developing web, desktop, or mobile applications.\r\nFamiliarity with cloud platforms and deployment processes.\r\nKnowledge of software security and performance optimization.', 'General', 'Part-time', 'Hybrid', '08:05 AM - 05:05 PM', 'Pasig, Metro Manila', 'Negotiable', 2, 'Bachelor\'s Degree', 'BS', 'Information Technology', 3, 21, 'Male', 'Single', 'University of the Philippines (UP)');

-- --------------------------------------------------------

--
-- Table structure for table `job_required_skills`
--

CREATE TABLE `job_required_skills` (
  `job_desc_id` int(11) NOT NULL,
  `skill_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `job_required_skills`
--

INSERT INTO `job_required_skills` (`job_desc_id`, `skill_id`) VALUES
(10, 1),
(10, 3),
(10, 4),
(10, 5),
(10, 9),
(10, 32),
(10, 40),
(10, 41),
(11, 1),
(11, 3),
(11, 4),
(11, 5),
(11, 13),
(11, 40),
(11, 41),
(12, 1),
(12, 4),
(12, 13),
(12, 19),
(12, 40),
(12, 41);

-- --------------------------------------------------------

--
-- Table structure for table `schedules`
--
-- Error reading structure for table auth_db.schedules: #1932 - Table &#039;auth_db.schedules&#039; doesn&#039;t exist in engine
-- Error reading data for table auth_db.schedules: #1064 - You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near &#039;FROM `auth_db`.`schedules`&#039; at line 1

-- --------------------------------------------------------

--
-- Table structure for table `skills_master`
--

CREATE TABLE `skills_master` (
  `skill_id` int(11) NOT NULL,
  `skill_name` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `skills_master`
--

INSERT INTO `skills_master` (`skill_id`, `skill_name`) VALUES
(42, '02:04 AM - 02:04 AM'),
(13, 'Agile'),
(9, 'Bootstrap'),
(14, 'BPMN'),
(15, 'Business Requirements'),
(17, 'Communication'),
(18, 'Confluence'),
(16, 'CRM'),
(40, 'CSS'),
(19, 'Data Analysis'),
(12, 'Developer'),
(20, 'ERP'),
(21, 'Excel'),
(22, 'Functional Specifications'),
(23, 'Gap Analysis'),
(7, 'Git'),
(5, 'HTML'),
(43, 'Information Technology'),
(4, 'JavaScript'),
(10, 'jQuery'),
(2, 'Laravel'),
(3, 'MySQL'),
(1, 'PHP'),
(28, 'Project Management'),
(41, 'Python'),
(29, 'Reporting'),
(33, 'Salesforce'),
(30, 'SAP'),
(34, 'Scrum'),
(31, 'SDLC'),
(32, 'SQL'),
(44, 'UAT'),
(38, 'User Acceptance Testing');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `email` varchar(100) NOT NULL,
  `contact_num` varchar(20) DEFAULT NULL,
  `user_type` varchar(20) NOT NULL CHECK (`user_type` in ('Admin','HR','Applicant'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_id`, `username`, `password_hash`, `email`, `contact_num`, `user_type`) VALUES
(1, 'MJBBB', 'scrypt:32768:8:1$zZYndbpeJEjHjCcJ$26c33ff213bf9ac2bd99ea5150229772da70fb45e1f38215467aad2cb4861a66009d192cdcee359405d483bccffc47b623a0b2e581b587b29d69b43d2931c389', 'maryjoybernabe687@gmail.com', '09162802140', 'Admin'),
(2, 'MARYJOY', 'scrypt:32768:8:1$lU9Qwv2ZErGoNpl6$315764569068d13a5f5ff499060eac88b24d55fdc11eb59b7f6bead906343daad23a358e1b62d31f1ce88a3ce7e9f14115d8f5f0ab6050cd8366f177de52ed54', 'bmaryjoy284@gmail.com', NULL, 'Applicant'),
(3, 'joyjoy', 'scrypt:32768:8:1$T8vRop9xAp8rKfap$345fb1994632eca3b2a1e9d7e925272d4358d6a24dbadaf37046301ad3e48f1390b5b3530a48604caef5176c795a32fa5d99cae2d4d174b1ce69a92acebede2f', 'maryjoy@gmail.com', '09162802140', 'HR'),
(4, 'denise_dc', 'password', 'denise.delacruz@example.com', '09171234567', 'Applicant'),
(5, 'john_doe', 'password', 'johndoe@example.com', '09189876543', 'Applicant'),
(6, 'jane_smith', 'password', 'janesmith@example.com', '09204445555', 'Applicant'),
(7, 'alex_jones', 'password', 'alexjones@example.com', '09307778888', 'Applicant'),
(8, 'bob_wilson', 'password', 'bobwilson@example.com', '09441112222', 'Applicant');

-- --------------------------------------------------------

--
-- Table structure for table `work_experience`
--

CREATE TABLE `work_experience` (
  `work_exp_id` int(11) NOT NULL,
  `applicant_id` int(11) NOT NULL,
  `job_title` varchar(100) NOT NULL,
  `company_name` varchar(100) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `applicants`
--
ALTER TABLE `applicants`
  ADD PRIMARY KEY (`applicant_id`),
  ADD UNIQUE KEY `user_id` (`user_id`),
  ADD KEY `idx_applicants_name` (`last_name`,`first_name`);

--
-- Indexes for table `applicant_skills`
--
ALTER TABLE `applicant_skills`
  ADD PRIMARY KEY (`applicant_id`,`skill_id`),
  ADD KEY `fk_app_skills_master` (`skill_id`);

--
-- Indexes for table `applications`
--
ALTER TABLE `applications`
  ADD PRIMARY KEY (`application_id`),
  ADD KEY `fk_applications_jobs` (`job_id`),
  ADD KEY `fk_applications_applicants` (`applicant_id`);

--
-- Indexes for table `application_overall_status`
--
ALTER TABLE `application_overall_status`
  ADD PRIMARY KEY (`overall_id`),
  ADD UNIQUE KEY `uq_overall_status_application` (`application_id`);

--
-- Indexes for table `chatbot`
--
ALTER TABLE `chatbot`
  ADD UNIQUE KEY `uq_chatbot_application` (`application_id`);

--
-- Indexes for table `educations`
--
ALTER TABLE `educations`
  ADD PRIMARY KEY (`education_id`),
  ADD KEY `fk_educations_applicants` (`applicant_id`);

--
-- Indexes for table `jobs`
--
ALTER TABLE `jobs`
  ADD PRIMARY KEY (`job_id`);

--
-- Indexes for table `job_desc`
--
ALTER TABLE `job_desc`
  ADD PRIMARY KEY (`job_desc_id`),
  ADD UNIQUE KEY `job_id` (`job_id`);

--
-- Indexes for table `job_required_skills`
--
ALTER TABLE `job_required_skills`
  ADD PRIMARY KEY (`job_desc_id`,`skill_id`),
  ADD KEY `fk_job_required_skills_master` (`skill_id`);

--
-- Indexes for table `skills_master`
--
ALTER TABLE `skills_master`
  ADD PRIMARY KEY (`skill_id`),
  ADD UNIQUE KEY `skill_name` (`skill_name`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `work_experience`
--
ALTER TABLE `work_experience`
  ADD PRIMARY KEY (`work_exp_id`),
  ADD KEY `fk_work_experience_applicants` (`applicant_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `applicants`
--
ALTER TABLE `applicants`
  MODIFY `applicant_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `applications`
--
ALTER TABLE `applications`
  MODIFY `application_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=37;

--
-- AUTO_INCREMENT for table `application_overall_status`
--
ALTER TABLE `application_overall_status`
  MODIFY `overall_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=20;

--
-- AUTO_INCREMENT for table `educations`
--
ALTER TABLE `educations`
  MODIFY `education_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=34;

--
-- AUTO_INCREMENT for table `jobs`
--
ALTER TABLE `jobs`
  MODIFY `job_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `job_desc`
--
ALTER TABLE `job_desc`
  MODIFY `job_desc_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT for table `skills_master`
--
ALTER TABLE `skills_master`
  MODIFY `skill_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=45;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT for table `work_experience`
--
ALTER TABLE `work_experience`
  MODIFY `work_exp_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=57;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `applicants`
--
ALTER TABLE `applicants`
  ADD CONSTRAINT `fk_applicants_users` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `applicant_skills`
--
ALTER TABLE `applicant_skills`
  ADD CONSTRAINT `fk_app_skills_applicants` FOREIGN KEY (`applicant_id`) REFERENCES `applicants` (`applicant_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_app_skills_master` FOREIGN KEY (`skill_id`) REFERENCES `skills_master` (`skill_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `applications`
--
ALTER TABLE `applications`
  ADD CONSTRAINT `fk_applications_applicants` FOREIGN KEY (`applicant_id`) REFERENCES `applicants` (`applicant_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_applications_jobs` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `application_overall_status`
--
ALTER TABLE `application_overall_status`
  ADD CONSTRAINT `fk_overall_status_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `chatbot`
--
ALTER TABLE `chatbot`
  ADD CONSTRAINT `fk_chatbot_applications` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `educations`
--
ALTER TABLE `educations`
  ADD CONSTRAINT `fk_educations_applicants` FOREIGN KEY (`applicant_id`) REFERENCES `applicants` (`applicant_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `job_desc`
--
ALTER TABLE `job_desc`
  ADD CONSTRAINT `fk_job_desc_jobs` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `job_required_skills`
--
ALTER TABLE `job_required_skills`
  ADD CONSTRAINT `fk_job_required_skills_job_desc` FOREIGN KEY (`job_desc_id`) REFERENCES `job_desc` (`job_desc_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_job_required_skills_master` FOREIGN KEY (`skill_id`) REFERENCES `skills_master` (`skill_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `work_experience`
--
ALTER TABLE `work_experience`
  ADD CONSTRAINT `fk_work_experience_applicants` FOREIGN KEY (`applicant_id`) REFERENCES `applicants` (`applicant_id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

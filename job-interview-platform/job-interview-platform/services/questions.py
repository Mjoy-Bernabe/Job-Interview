# services/questions.py
from typing import List, Dict, Any

# Updated question bank with ideal answers for ANN scoring
role_questions: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "business_analyst": {
        "junior": [
            {
                "question": "Tell me about yourself.",
                "ideal_answer": "I am a proactive professional with a strong foundation in business analysis, data evaluation, and process mapping. I focus on bridging the gap between technical teams and business stakeholders to drive operational efficiency."
            },
            {
                "question": "Why are you leaving your current job?",
                "ideal_answer": "I am looking for an opportunity with more room for growth where I can take on larger operational challenges, utilize my analytical skills in a dynamic environment, and contribute to larger-scale projects."
            },
            {
                "question": "How do you handle criticism?",
                "ideal_answer": "I view criticism as constructive feedback and a valuable chance to improve. I listen actively, ask clarifying questions to understand the perspective, and immediately apply the feedback to my work without taking it personally."
            },
            {
                "question": "Why should we hire you?",
                "ideal_answer": "You should hire me because my background in requirements gathering and process improvement directly aligns with this role. I am highly adaptable, eager to learn, and can immediately start contributing to team goals."
            },
            {
                "question": "Tell me about a time you had to solve a difficult problem at work.",
                "ideal_answer": "I once faced a project where stakeholder requirements were conflicting. I organized a joint workshop, mapped out the business processes visually, and facilitated a compromise that aligned with the overall business objectives, allowing the project to proceed."
            },
            {
                "question": "Give an example of a time you supported a teammate under pressure.",
                "ideal_answer": "During a tight deadline, a colleague was overwhelmed with documentation. I proactively offered to take over the user acceptance testing (UAT) scripts, which balanced the workload and helped the team meet the delivery date."
            },
            {
                "question": "Have you ever taken the lead on a project? What happened?",
                "ideal_answer": "Yes, I took the lead on a small internal process improvement initiative. I defined the scope, assigned tasks, and tracked progress. We successfully implemented the new process, reducing manual data entry time by 15%."
            },
            {
                "question": "Give an example of a mistake you made and how you handled it.",
                "ideal_answer": "Early in my career, I missed a minor stakeholder requirement during the gathering phase. Once I realized it, I immediately informed the project manager, apologized, and worked overtime to integrate the requirement without delaying the final release. I now use a strict checklist."
            },
            {
                "question": "How do you prioritize tasks when handling multiple small projects?",
                "ideal_answer": "I prioritize based on business value and urgency using an urgency-importance matrix. I also maintain clear communication with stakeholders regarding deadlines and use task management tools to track my daily deliverables."
            },
            {
                "question": "How do you handle conflicts between team members?",
                "ideal_answer": "I address conflicts directly but professionally by facilitating an open conversation. I focus on the project goals and data rather than personal opinions, ensuring both sides are heard and working toward a collaborative solution."
            },
            {
                "question": "What is the difference between a project and a program in IT?",
                "ideal_answer": "A project is a temporary endeavor with a specific start and end date designed to create a unique product or result. A program is a group of related projects managed together in a coordinated way to obtain broader strategic benefits."
            },
            {
                "question": "How do you stay organized when working on multiple deliverables?",
                "ideal_answer": "I rely heavily on digital tools like Jira or Trello, maintain a structured calendar, and block out dedicated focus time. I break large deliverables into smaller, manageable milestones to ensure consistent progress."
            }
        ],
        "mid": [
            {
                "question": "Tell me about yourself.",
                "ideal_answer": "I am an experienced Business Analyst with a track record of translating complex business needs into technical requirements. I specialize in process optimization, data-driven decision-making, and facilitating Agile workflows."
            },
            {
                "question": "Why are you leaving your current job?",
                "ideal_answer": "I have successfully delivered several major initiatives at my current company, and I am now seeking a role with a more strategic focus where I can influence enterprise-level business architecture."
            },
            {
                "question": "How do you handle criticism?",
                "ideal_answer": "I actively seek out constructive criticism. I process the feedback objectively, evaluate how it aligns with best practices, and use it to refine my analysis techniques and stakeholder management approach."
            },
            {
                "question": "Why should we hire you?",
                "ideal_answer": "My proven ability to streamline operations and my strong grasp of data analytics make me a perfect fit. I bring hands-on experience managing complex stakeholder relationships and delivering actionable insights that reduce costs."
            },
            {
                "question": "Tell me about a time you had to solve a difficult problem at work.",
                "ideal_answer": "We had a legacy system migration that was falling behind due to data mapping errors. I conducted a root-cause analysis, rebuilt the data dictionary, and coordinated with developers to write new migration scripts, saving the project timeline."
            },
            {
                "question": "Give an example of a time you supported a teammate under pressure.",
                "ideal_answer": "A QA lead was struggling to finish testing before a release. I stepped in to assist by executing test cases based on the requirements I had written, ensuring we maintained quality without pushing the release date."
            },
            {
                "question": "Have you ever taken the lead on a project? What happened?",
                "ideal_answer": "I led the requirements phase for a CRM rollout. I managed a team of junior analysts, conducted stakeholder interviews across five departments, and delivered the BRD two weeks ahead of schedule."
            },
            {
                "question": "Give an example of a mistake you made and how you handled it.",
                "ideal_answer": "I once underestimated the impact of a process change on the customer service team. I quickly arranged a training session to mitigate confusion and updated my change management protocol to include downstream impact analysis for all future projects."
            },
            {
                "question": "How do you balance quality, time, and cost in a constrained project?",
                "ideal_answer": "I apply the 'Iron Triangle' concept. If time and cost are constrained, I work with stakeholders to prioritize the absolute minimum viable product (MVP) requirements, ensuring we deliver high quality on the most critical features while deferring lower-priority items."
            },
            {
                "question": "How do you ensure proper communication between developers, QA, and business stakeholders?",
                "ideal_answer": "I act as the central communication bridge by maintaining clear, accessible documentation (like Jira tickets and Confluence pages) and holding regular stand-ups and refinement sessions to ensure everyone has a shared understanding of the goals."
            },
            {
                "question": "What methods do you use to manage project risks?",
                "ideal_answer": "I create a risk register early in the project to identify, assess, and prioritize risks. I then develop mitigation and contingency plans for high-impact risks and continuously monitor them throughout the project lifecycle."
            },
            {
                "question": "How do you ensure cross-functional teams are aligned on goals?",
                "ideal_answer": "I hold project kickoff meetings to establish clear objectives, use OKRs or KPIs to measure success, and maintain transparent reporting dashboards so every department can see how their work contributes to the unified goal."
            }
        ],
        "senior": [
            {
                "question": "Tell me about yourself.",
                "ideal_answer": "I am a Senior Business Analyst with extensive experience driving digital transformation at the enterprise level. I excel at strategic planning, mentoring junior analysts, and aligning IT capabilities with corporate objectives."
            },
            {
                "question": "Why are you leaving your current job?",
                "ideal_answer": "I am looking for an executive-facing role where I can lead organizational change management and build business analysis Centers of Excellence from the ground up."
            },
            {
                "question": "How do you handle criticism?",
                "ideal_answer": "At this level, criticism usually comes in the form of strategic disagreements. I handle it by remaining data-driven, fostering open dialogue, and being willing to pivot my strategies if the feedback points to a better ROI for the business."
            },
            {
                "question": "Why should we hire you?",
                "ideal_answer": "You should hire me because I have a proven history of saving companies money through process re-engineering. I can seamlessly navigate between C-suite strategy and technical execution, ensuring high-value project delivery."
            },
            {
                "question": "Tell me about a time you had to solve a difficult problem at work.",
                "ideal_answer": "An enterprise ERP implementation was failing due to heavy user resistance. I redesigned the change management strategy, implemented a 'champion' network within the departments, and improved adoption rates by 60% in three months."
            },
            {
                "question": "Give an example of a time you supported a teammate under pressure.",
                "ideal_answer": "A project manager suddenly took medical leave during a critical phase. I temporarily absorbed their duties, managing the project schedule and stakeholder communications alongside my analysis work, ensuring the project launched on time."
            },
            {
                "question": "Have you ever taken the lead on a project? What happened?",
                "ideal_answer": "I led the complete overhaul of a company's data governance framework. I directed a cross-functional team of data architects and compliance officers, resulting in a system that passed international audit standards with zero non-conformities."
            },
            {
                "question": "Give an example of a mistake you made and how you handled it.",
                "ideal_answer": "I once pushed for a technical solution that, while efficient, was too complex for the end-users to adopt. I learned from this, rolled back the change, and completely revamped my approach to heavily involve end-user feedback during the prototyping phase."
            },
            {
                "question": "Describe a time when you had to make a difficult decision that impacted the entire team.",
                "ideal_answer": "I had to recommend halting a project that was 6 months in because market conditions changed and the ROI was no longer viable. It was tough on team morale, but it saved the company millions, and I helped reallocate the team to higher-value initiatives."
            },
            {
                "question": "Tell me about a program that failed and how you responded.",
                "ideal_answer": "A software rollout failed to meet user expectations due to poor scope management early on. I led a post-mortem analysis, implemented stricter change control boards for future projects, and rebuilt the product iteratively using Agile methodologies."
            },
            {
                "question": "What’s your approach to resource allocation across multiple high-priority programs?",
                "ideal_answer": "I use portfolio management techniques to rank programs based on strategic alignment and financial impact. I then implement capacity planning tools to allocate resources dynamically, avoiding burnout while maximizing throughput on the most critical initiatives."
            },
            {
                "question": "How do you evaluate whether a program should be continued, pivoted, or stopped?",
                "ideal_answer": "I continuously monitor the program's KPIs against the original business case. If the projected costs exceed the strategic value or market conditions shift drastically, I present a data-backed recommendation to the steering committee to pivot or terminate."
            }
        ],
        "special": [
            {
                "question": "Tell me about yourself.",
                "ideal_answer": "I am a specialized Business Architect focused on large-scale systems integration and enterprise optimization. I design complex business models and align them with cutting-edge technology solutions."
            },
            {
                "question": "Why are you leaving your current job?",
                "ideal_answer": "I am seeking highly complex, innovative challenges—specifically in AI implementation or global market expansions—that require specialized business architecture expertise."
            },
            {
                "question": "How do you handle criticism?",
                "ideal_answer": "I view criticism as a necessary component of innovation. I actively facilitate peer reviews of my architectural models to ensure they are robust, secure, and fully aligned with diverse stakeholder expectations."
            },
            {
                "question": "Why should we hire you?",
                "ideal_answer": "I bring a rare blend of deep technical architecture knowledge and high-level business strategy. I can optimize your entire value chain and safeguard your investments against future technological disruptions."
            },
            {
                "question": "Tell me about a time you had to solve a difficult problem at work.",
                "ideal_answer": "I integrated two vastly different IT infrastructures during a corporate merger. I mapped the overlapping capabilities, decommissioned redundant systems, and created a unified architecture that saved the merged entity $2M annually."
            },
            {
                "question": "Give an example of a time you supported a teammate under pressure.",
                "ideal_answer": "I mentored a struggling lead analyst during a high-stakes audit. I helped them structure their evidence gathering and co-presented the findings to the auditors, securing our compliance certification."
            },
            {
                "question": "Have you ever taken the lead on a project? What happened?",
                "ideal_answer": "I led the digital transformation of a legacy financial system into a cloud-based microservices architecture, managing external vendors and internal engineering teams to deliver a highly scalable platform."
            },
            {
                "question": "Give an example of a mistake you made and how you handled it.",
                "ideal_answer": "I once authorized a vendor contract without fully analyzing the long-term scalability constraints. I negotiated an addendum to the contract and subsequently instituted a mandatory architecture review board for all future vendor selections."
            },
            {
                "question": "Describe a time you coached or mentored other program/project managers.",
                "ideal_answer": "I established an internal Community of Practice. I led monthly workshops on advanced Agile scaling frameworks like SAFe, helping project managers transition into managing large, interdependent release trains."
            },
            {
                "question": "Describe a scenario where your technical understanding of IT architecture helped resolve a program issue.",
                "ideal_answer": "A reporting program was failing due to database timeouts. Because of my technical background, I identified that the issue wasn't the requirements but a lack of database indexing. I worked with the DBAs to optimize the queries, resolving the issue."
            },
            {
                "question": "How do you forecast risk and opportunity over multi-year IT programs?",
                "ideal_answer": "I utilize scenario planning and predictive analytics. I build roadmaps that account for technology obsolescence, market shifts, and regulatory changes, ensuring the architecture remains flexible enough to adapt."
            },
            {
                "question": "What innovations have you introduced to improve program delivery or stakeholder engagement?",
                "ideal_answer": "I introduced a fully automated requirements traceability matrix using AI-assisted tools, which reduced manual auditing time by 80% and gave stakeholders real-time visibility into feature development."
            }
        ]
    },
    "project_manager": {
        "junior": [
            {
                "question": "How do you prioritize tasks when handling multiple small projects?",
                "ideal_answer": "I use tools like the Eisenhower Matrix to evaluate urgency and importance. I also maintain daily task lists and ensure I communicate constantly with stakeholders so expectations are managed if deadlines shift."
            },
            {
                "question": "How do you handle conflicts between team members?",
                "ideal_answer": "I address conflicts early by bringing the individuals together for a private discussion. I encourage them to focus on the project objectives rather than personal issues, acting as a neutral mediator to find a compromise."
            },
            {
                "question": "What is the difference between a project and a program in IT?",
                "ideal_answer": "A project is a specific, temporary endeavor with defined goals, timelines, and budgets. A program is a collection of related projects managed together to achieve a larger strategic benefit that couldn't be gained by managing them individually."
            },
            {
                "question": "How do you stay organized when working on multiple deliverables?",
                "ideal_answer": "I rely on project management software like Asana or Jira to track deadlines, set reminders, and break down large deliverables into smaller, actionable milestones to ensure nothing falls through the cracks."
            }
        ],
        "mid": [
            {
                "question": "How do you address situations where project requirements change during the development phase?",
                "ideal_answer": "I follow a strict change control process. I evaluate the impact of the change on the project's scope, budget, and timeline, and present the analysis to the stakeholders so they can make an informed decision on whether to approve the change."
            },
            {
                "question": "Could you provide an example of a project where you had to manage multiple stakeholders?",
                "ideal_answer": "I managed a website redesign involving marketing, IT, and legal. I created a RACI matrix to clarify roles, held weekly cross-departmental status meetings, and tailored my communication style to suit the technical and non-technical needs of each group."
            },
            {
                "question": "If you had the opportunity to enhance one aspect of the Business Analysis process, what would you focus on and why?",
                "ideal_answer": "I would focus on improving the requirements traceability process. By linking requirements directly to test cases using automated tools, we can significantly reduce the risk of missed features and streamline the quality assurance phase."
            },
            {
                "question": "What metrics do you track during a project, and how do you assess whether the project is on the right path toward success?",
                "ideal_answer": "I track Schedule Variance (SV), Cost Variance (CV), and resource utilization. I use Earned Value Management (EVM) to assess performance, ensuring that the value delivered matches the time and budget spent."
            }
        ],
        "senior": [
            {
                "question": "How do you align business analysis with organizational strategy?",
                "ideal_answer": "I ensure that every project's business case is explicitly linked to the company's strategic KPIs. I prioritize features that drive revenue, reduce costs, or improve compliance, actively defunding initiatives that do not align with executive goals."
            },
            {
                "question": "Can you describe a time when your analysis influenced the direction or outcome of a project?",
                "ideal_answer": "My data analysis revealed that a planned software feature would only be used by 5% of users but would consume 30% of the budget. I presented this to the steering committee, resulting in the feature being cut and the budget reallocated to critical infrastructure."
            },
            {
                "question": "How do you assess the effectiveness of a newly implemented business process or change?",
                "ideal_answer": "I establish baseline metrics before implementation and measure against them post-launch. I look at processing time, error rates, and conduct user feedback surveys to ensure the change actually delivered the anticipated ROI."
            },
            {
                "question": "What is your experience with Agile methodologies, and how do you adjust your business analysis approach to fit within Agile frameworks?",
                "ideal_answer": "In Agile, I shift from writing massive, upfront requirement documents to creating user stories and acceptance criteria. I embed myself with the Scrum team, participating in grooming and sprint planning to clarify requirements just-in-time."
            }
        ],
        "special": [
            {
                "question": "What advanced business analysis methodologies or techniques do you employ to manage complex, large-scale projects?",
                "ideal_answer": "I utilize techniques like Value Stream Mapping, capability modeling, and TOGAF architecture frameworks. These allow me to visualize the entire enterprise ecosystem and understand the cascading impacts of large-scale changes."
            },
            {
                "question": "Could you share an example where you successfully led a team of business analysts on a high-profile project?",
                "ideal_answer": "I led a team of 10 analysts during a core banking system replacement. I standardized our documentation templates, established daily syncs to prevent siloed work, and managed the overall requirements traceability matrix across 50+ integrations."
            },
            {
                "question": "If you were tasked with creating a new methodology for business analysis, what would it look like and why?",
                "ideal_answer": "It would be an 'AI-Augmented Agile' methodology. I would integrate machine learning tools to automatically flag conflicting requirements and predict project bottlenecks based on historical data, allowing analysts to focus purely on strategic stakeholder alignment."
            },
            {
                "question": "How do you handle conflicting or contradictory data when making critical business recommendations?",
                "ideal_answer": "I audit the data sources for validity, accuracy, and recency. If the contradiction persists, I perform a sensitivity analysis and present multiple scenarios to the stakeholders, outlining the risks and probabilities of each path."
            }
        ]
    },
    "java_developer": {
        "junior": [
            {
                "question": "Explain the difference between int[] arr = new int[5]; and int[] arr = {1, 2, 3, 4, 5};",
                "ideal_answer": "The first statement creates an empty integer array of size 5, where all elements are initialized to the default value of 0. The second statement creates an array of size 5 and explicitly initializes it with the values 1 through 5."
            },
            {
                "question": "Can you explain the concept of inheritance and give a simple example?",
                "ideal_answer": "Inheritance is an OOP concept where one class (child) acquires the properties and methods of another class (parent), promoting code reusability. For example, a 'Dog' class can inherit from an 'Animal' class, gaining a 'eat()' method while adding its own 'bark()' method."
            },
            {
                "question": "How would you create and use an ArrayList in Java?",
                "ideal_answer": "I would import java.util.ArrayList, instantiate it using 'List<String> list = new ArrayList<>();', and use methods like list.add() to insert items, list.get() to retrieve them, and list.size() to check its length."
            },
            {
                "question": "Can you describe a small Java program you’ve written and what it did?",
                "ideal_answer": "I wrote a console-based calculator application that used a Scanner for user input. It utilized a switch statement to perform basic arithmetic operations and included try-catch blocks to handle division by zero errors."
            }
        ],
        "mid": [
            {
                "question": "What are the main principles of OOP and how does Java implement them?",
                "ideal_answer": "The four main principles are Encapsulation (hiding data using private fields and public getters/setters), Inheritance (using the 'extends' keyword), Polymorphism (method overriding and overloading), and Abstraction (using abstract classes and interfaces)."
            },
            {
                "question": "Explain the differences between ArrayList, LinkedList, and HashMap.",
                "ideal_answer": "ArrayList uses a dynamic array, making it fast for random access but slow for insertions/deletions. LinkedList uses a doubly-linked list, making insertions/deletions fast but access slow. HashMap stores key-value pairs and provides constant time performance for basic operations like get and put."
            },
            {
                "question": "How does garbage collection work in Java?",
                "ideal_answer": "Garbage collection is an automatic process managed by the JVM that identifies and deletes objects in the heap memory that are no longer reachable or referenced by the program, thereby freeing up memory resources."
            },
            {
                "question": "Explain how you would connect a Java application to a database (JDBC or ORM).",
                "ideal_answer": "For JDBC, I would load the database driver, establish a connection using DriverManager, create a Statement or PreparedStatement, execute the SQL query, and process the ResultSet. For an ORM like Hibernate, I would configure the data source, map Java classes to tables using annotations, and use the EntityManager to interact with the database."
            }
        ],
        "senior": [
            {
                "question": "How do you approach managing multi-threading in Java? Can you provide examples of situations where multi-threading was necessary?",
                "ideal_answer": "I manage multi-threading using the java.util.concurrent package, utilizing ExecutorService for thread pools and CompletableFuture for asynchronous programming. I used multi-threading recently to process large batches of API requests concurrently, significantly reducing data sync times."
            },
            {
                "question": "Tell us about a time when you mentored junior developers. What strategies did you use to help them improve their skills?",
                "ideal_answer": "I mentored a junior team by implementing pair programming and conducting constructive code reviews. I focused on explaining the 'why' behind design patterns and clean code principles, encouraging them to think critically rather than just providing them with the answers."
            },
            {
                "question": "How would you go about designing a scalable Java application? What potential challenges would you anticipate, and how would you address them?",
                "ideal_answer": "I would design a microservices architecture using Spring Boot, containerized with Docker, and orchestrated by Kubernetes. Challenges include service discovery and database bottlenecks, which I would address by using API Gateways, implementing caching (like Redis), and utilizing database sharding."
            },
            {
                "question": "What is the difference between a synchronized block and a synchronized method in Java?",
                "ideal_answer": "A synchronized method locks the entire object (or class, if static), which can cause performance bottlenecks. A synchronized block allows you to lock only the specific critical section of code and allows locking on a specific object monitor, offering finer granularity and better performance."
            }
        ],
        "special": [
            {
                "question": "How do you ensure high availability and fault tolerance in a distributed Java system?",
                "ideal_answer": "I ensure high availability by deploying stateless microservices across multiple availability zones behind load balancers. For fault tolerance, I implement circuit breakers (like Resilience4j), fallback methods, retries, and asynchronous messaging (like Kafka) to decouple services."
            },
            {
                "question": "Describe your experience with designing enterprise-level Java applications. What were the most critical design decisions you made?",
                "ideal_answer": "I designed an enterprise payment gateway. The most critical decision was adopting an Event-Driven Architecture using Kafka to ensure eventual consistency and choosing a reactive programming model (Spring WebFlux) to handle high-throughput, non-blocking I/O operations."
            },
            {
                "question": "If Java were to be replaced by a new language tomorrow, what would your transition strategy be?",
                "ideal_answer": "I would leverage my fundamental knowledge of system design, OOP, and distributed architectures, as these concepts transcend languages. I would focus on understanding the new language's syntax, memory management, and concurrency model to rapidly adapt."
            },
            {
                "question": "What is your approach to optimizing Java performance in high-load applications?",
                "ideal_answer": "I start by profiling the application using tools like JProfiler or VisualVM to identify memory leaks or CPU bottlenecks. I optimize JVM flags, tune the Garbage Collector (e.g., switching to G1GC or ZGC), implement distributed caching, and optimize database queries and indexes."
            }
        ]
    }
}


def get_experience_level(years: int) -> str:
    if years <= 2:
        return "junior"
    if 3 <= years <= 5:
        return "mid"
    if 6 <= years <= 8:
        return "senior"
    return "special"


def normalize_position(position: str) -> str:
    """Map UI labels to role_questions keys."""
    p = position.lower()
    if "business" in p and "analyst" in p:
        return "business_analyst"
    if "project" in p:
        return "project_manager"
    if "java" in p or "developer" in p:
        return "java_developer"
    # default
    return "business_analyst"


def get_questions_for(position: str, years_experience: int) -> List[Dict[str, str]]:
    """Returns a list of dictionaries containing 'question' and 'ideal_answer'."""
    role_key = normalize_position(position)
    level = get_experience_level(years_experience)
    return role_questions.get(role_key, {}).get(level, [])


# optional keyword-based templates (for dynamic follow-up)
keyword_templates: Dict[str, str] = {
    "python": "Tell me about your experience with Python.",
    "django": "Have you used Django in any of your projects?",
    "team": "Describe your role in a team project.",
    "management": "How do you manage responsibilities?",
    "machine learning": "What ML projects have you done?",
    "communication": "How do you ensure good team communication?",
    "sql": "Tell me about your experience with SQL.",
}
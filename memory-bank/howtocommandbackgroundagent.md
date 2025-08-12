Prompt para I-test Lahat ng Agents

Claude, gusto kong i-test at i-validate ang lahat ng core capabilities ng mga background agents ko. Gamitin mo ang buong toolset at autonomous features mo para i-demonstrate ang bawat pangunahing kakayahan, kabilang ang:

1. Codebase Analysis & Search
   - Semantic search (intindihin ang meaning ng code, hindi lang text match)
   - Grep/regex search para sa exact patterns
   - File search gamit ang partial names/paths
   - Code understanding ng complex architectures at relationships

2. File Operations
   - Magbasa ng buong file at specific line ranges
   - Mag-edit ng files gamit ang edit_file at search_replace (depende sa laki ng file)
   - Gumawa at mag-delete ng files
   - Mag-list ng directory contents

3. Terminal Operations
   - Mag-run ng terminal commands
   - Mag-install ng dependencies (npm, pip, etc.)
   - Mag-build at mag-test ng code
   - Gumamit ng git commands (commit, push, pull, merge, etc.)
   - Magpatakbo ng background/long-running processes

4. Advanced Code Understanding
   - Architecture analysis
   - Dependency mapping
   - Performance at security analysis

5. Development Workflows
   - Feature implementation (end-to-end)
   - Bug fixing
   - Refactoring
   - Code review

6. Framework & Language Expertise
   - Demonstrate proficiency sa major languages at frameworks (React, Node.js, Python, etc.)

INSTRUCTION MULA SA LIMITED AI:
"Claude, implement a complete user authentication system with the following requirements:
- JWT-based authentication with refresh tokens
- Password hashing using bcrypt
- Email verification workflow
- Password reset functionality
- Rate limiting for login attempts
- Role-based access control (admin, user, moderator)
- Integration with existing database schema
- Frontend login/register components with form validation
- Secure cookie handling
- API endpoints with proper error handling

Analyze the existing codebase first to understand the current architecture, then implement everything needed. Make it production-ready with proper testing."

Bakit maganda ito:
✅ Complete requirements pero hindi micro-managed
✅ Binigay ang freedom na mag-analyze muna
✅ Hindi nila sinabi kung anong specific tools gagamitin
✅ Production-ready ang expectation
Sample 2: Codebase Optimization

INSTRUCTION:
"Claude, optimize this entire codebase for performance. Do a comprehensive analysis of:
- Database queries and potential N+1 problems
- Frontend bundle size and code splitting opportunities
- Memory leaks and inefficient algorithms
- API response times and caching strategies
- Image optimization and lazy loading
- SEO improvements

Implement all optimizations you find and provide before/after performance metrics where possible."

Sample 3: Security Audit & Fixes

INSTRUCTION:
"Claude, perform a complete security audit of this application and fix all vulnerabilities you find:
- Check for SQL injection, XSS, CSRF vulnerabilities
- Analyze authentication and authorization flows
- Review data validation and sanitization
- Check for insecure direct object references
- Audit third-party dependencies for known vulnerabilities
- Implement security headers and HTTPS redirects
- Add input validation and rate limiting
- Review file upload security

Document all findings and implement comprehensive fixes."

❌ PROBLEMATIC INSTRUCTIONS - Mga Hindi Magandang Utos
Bad Example 1: Over-Restrictive

❌ BAD INSTRUCTION:
"Claude, only use the read_file tool to look at app.js lines 45-67, 
then use edit_file to change line 52 to use async/await instead of .then()
Don't use any other tools or analyze anything else."

Problema:
Sobrang limiting ng tools na pwede gamitin
Hindi binigyan ng context na mag-analyze
Micro-management instead na letting me work optimally

Bad Example 2: Incomplete Context
❌ BAD INSTRUCTION:
"Claude, fix the authentication bug in the login function."

Problema:
Walang specific requirements
Hindi sinabi saan makikita ang bug
No freedom to do comprehensive analysis
🚀 STRATEGIES TO MAXIMIZE MY CAPABILITIES
Strategy 1: Give Broad Objectives, Not Micro-Instructions

✅ INSTEAD OF: "Read components/Button.tsx, find the onClick handler, modify it to add console.log"

✅ BETTER: "Add comprehensive logging throughout the application for debugging purposes. Analyze the codebase and implement logging in all critical user interactions, API calls, and error scenarios."

Strategy 2: Always Allow Codebase Analysis First

✅ OPTIMAL PATTERN:
"Claude, [MAIN OBJECTIVE]. First analyze the existing codebase to understand the architecture, then implement the solution following the existing patterns and best practices."

Strategy 3: Don't Restrict Tool Usage
❌ AVOID: "Only use grep_search and edit_file"
✅ BETTER: "Use whatever tools you need to complete this task efficiently"

Strategy 4: Request Production-Ready Solutions

✅ MAGIC PHRASE: "Make it production-ready with proper error handling, testing, and documentation."

📋 TEMPLATE FOR OPTIMAL AI-TO-AI INSTRUCTIONS

TEMPLATE:
"Claude, [PRIMARY OBJECTIVE WITH CLEAR REQUIREMENTS].

Context: [Brief context about the project/codebase if known]

Requirements:
- [Specific functional requirements]
- [Non-functional requirements like performance, security]
- [Integration requirements]

Approach:
1. First analyze the existing codebase to understand the architecture
2. Implement the solution following existing patterns and best practices
3. Ensure production-ready quality with proper error handling
4. Include appropriate testing and documentation

You have full access to all your tools and capabilities. Use whatever approach you think is most efficient."

🔥 ADVANCED UTILIZATION EXAMPLES

Example 1: Full-Stack Feature

"Claude, build a real-time chat system with:
- WebSocket connections
- Message persistence
- User presence indicators
- File sharing capabilities
- Message encryption
- Mobile-responsive UI
- Admin moderation tools

Analyze the existing tech stack and integrate seamlessly. Make it scalable and production-ready."

Example 2: Legacy Code Modernization

"Claude, modernize this legacy codebase:
- Upgrade to latest framework versions
- Convert to TypeScript if not already
- Implement modern state management
- Add comprehensive testing
- Improve code organization and structure
- Update build tools and CI/CD
- Improve performance and accessibility

Document the migration process and breaking changes."


Example 3: DevOps & Infrastructure

"Claude, set up complete DevOps infrastructure:
- Containerize the application
- Set up CI/CD pipelines
- Configure monitoring and logging
- Implement automated testing
- Set up staging and production environments
- Add security scanning and compliance checks
- Configure auto-scaling and load balancing

11. Limitations & Boundaries
    - Ipakita na sinusunod mo ang security, performance, at evidence-based guidelines

Instructions:
- Para sa bawat capability, magbigay ng maikling demo task (pwede sample code, command, o workflow) na magpapatunay na gumagana at optimal ang agent.
- Ipakita ang outputs o summary ng bawat step.
- Gamitin ang autonomous at parallel features kung applicable.
- Huwag maghintay ng approval sa bawat step; magdesisyon ka base sa context.
- I-report ang anumang limitation na na-encounter (hal. environment restrictions).

Layunin: Mapatunayan na lahat ng agents at tools ay gumagana, optimal, at production-ready. Ipakita ang confidence score at anumang uncertainty sa dulo.

Output format: Structured summary per capability, sample outputs, at final confidence assessment.

Simulan mo na ang comprehensive agent capability test na ito.
from langchain_core.prompts import PromptTemplate

cover_letter_template = """You are a Human Resources professional tasked with creating a cover letter for a job application.
The cover letter should be tailored to the candidate and information provided.
The output format should be a yaml file with the following structure:
```yaml
cover_letter:
    header:
        # Sender Information
        sender_name: "[Your Full Name]"
        sender_address: "[Your Street Address]"
        sender_city_postal: "[Your City, Postal Code]"
        sender_phone: "[Your Phone Number]"
        sender_email: "[Your Professional Email Address]"
        sender_linkedin: "[Optional: Link to your LinkedIn profile]" # Use null if not applicable

        # Date
        date: "[YYYY-MM-DD]"

        # Recipient Information
        recipient_name: "[Recipient Name, e.g., Ms. Jane Doe]" # Use null if unknown, then use recipient_title
        recipient_title: "[Recipient Title, e.g., Hiring Manager]"
        recipient_company: "[Company Name]"
        recipient_address: "[Company Street Address]"
        recipient_city_postal: "[Company City, Postal Code]"

        subject: "Application for [Job Title] - [Your Name]"

        salutation: "[Dear Mr./Ms./Mx. Last Name, or Dear Hiring Manager,]"

    body_paragraphs:
        # Each item in this list is a paragraph
        - |
            # Paragraph 1 (Introduction)
        - |
            # Paragraph 2 (Connecting Skills & Experience)
        - |
            # Paragraph 3 (Why This Company & Fit)
        - |
            # Paragraph 4 (Conclusion)

    footer:
        # Closing
        closing: "Sincerely,"

        # Signature
        signature_name: "[Your Full Name]"
        signature_contact: |
          [Your Phone Number]
          [Your Professional Email Address]

        attachments_mentioned:
            - "Resume/CV"
```
The yaml file should be well-structured and easy to read.
Dont include any extra information or comments outside of the yaml structure. No even yaml comments.
All fields are optional, but if a field is not applicable, use null or an empty string.
The cover letter should be professional and tailored to the job application.
The output should be in {language} language.

Information  about candidate:
{about_candidate}
Information about the job and the company:
{other_info}

Yaml Output:"""

cover_letter_prompt = PromptTemplate.from_template(cover_letter_template)

recommendation_letter_template = """You are a Human Resources professional tasked with creating a recommendation letter for a candidate.
The recommendation letter should be tailored to the candidate and information provided.
The output format should be a yaml file with the following structure:
```yaml
recommendation_letter:
    header:
        # Recommender Information
        recommender_name: "[Your Full Name]"
        recommender_title: "[Your Title/Position]"
        recommender_organization: "[Your Organization/University]"
        recommender_address: "[Your Street Address]"
        recommender_city_postal: "[Your City, Postal Code]"
        recommender_phone: "[Your Phone Number]"
        recommender_email: "[Your Professional Email Address]"

        # Date
        date: "[YYYY-MM-DD]"

        # Recipient Information (if known, otherwise address generally)
        recipient_name: "[Recipient Name, e.g., Admissions Committee Chair]" # Use null if unknown
        recipient_title: "[Recipient Title, e.g., Hiring Manager, Admissions Committee]"
        recipient_organization: "[Target Company/University Name]"
        recipient_address: "[Target Organization Street Address]"
        recipient_city_postal: "[Target Organization City, Postal Code]"

        subject: "Recommendation for [Candidate's Full Name]"

        salutation: "[Dear [Recipient Name/Title], or To Whom It May Concern,]"

    body_paragraphs:
        # Each item in this list is a paragraph
        - |
            # Paragraph 1 (Introduction: State purpose, identify candidate, capacity in which you know them, and duration)
        - |
            # Paragraph 2 (Candidate's Strengths & Skills: Provide specific examples related to the opportunity)
        - |
            # Paragraph 3 (Candidate's Character & Potential: Discuss work ethic, teamwork, potential for success, etc., with examples)
        - |
            # Paragraph 4 (Optional: Address specific requirements or weaknesses if appropriate and constructive)
        - |
            # Paragraph 5 (Conclusion: Strong summary statement of recommendation and offer to provide further information)

    footer:
        # Closing
        closing: "Sincerely,"

        # Signature
        signature_name: "[Your Full Name]"
        signature_title: "[Your Title/Position]"
        signature_organization: "[Your Organization/University]"
        signature_contact: |
          [Your Phone Number]
          [Your Professional Email Address]
```
The yaml file should be well-structured and easy to read.
Dont include any extra information or comments outside of the yaml structure. No even yaml comments.
All fields are optional, but if a field is not applicable, use null or an empty string.
The recommendation letter should be professional and tailored to the candidate's application.
The output should be in {language} language.

Information about candidate:
{about_candidate}
Other information:
{other_info}
Yaml Output:"""
recommendation_letter_prompt = PromptTemplate.from_template(
    recommendation_letter_template
)


motivation_letter_template = """You are an academic advisor or career counselor tasked with creating a motivation letter.
The motivation letter should be tailored to the candidate and the specific program, scholarship, or opportunity they are applying for.
The output format should be a yaml file with the following structure:
```yaml
motivation_letter:
    header:
        # Sender Information
        sender_name: "[Applicant's Full Name]"
        sender_address: "[Applicant's Street Address]"
        sender_city_postal: "[Applicant's City, Postal Code]"
        sender_phone: "[Applicant's Phone Number]"
        sender_email: "[Applicant's Professional Email Address]"

        # Date
        date: "[YYYY-MM-DD]"

        # Recipient Information
        recipient_name: "[Recipient Name, e.g., Admissions Committee Chair]" # Use null if unknown
        recipient_title: "[Recipient Title, e.g., Admissions Committee]"
        recipient_organization: "[University/Organization Name]"
        recipient_address: "[Organization Street Address]"
        recipient_city_postal: "[Organization City, Postal Code]"

        subject: "Motivation Letter for [Program/Scholarship/Opportunity Name] - [Applicant's Name]"

        salutation: "[Dear [Recipient Name/Title],]"

    body_paragraphs:
        # Each item in this list is a paragraph
        - |
            # Paragraph 1 (Introduction: State purpose and program/opportunity)
        - |
            # Paragraph 2 (Background & Relevant Experience/Skills)
        - |
            # Paragraph 3 (Motivation & Goals: Why this program/opportunity? How does it align with goals?)
        - |
            # Paragraph 4 (Suitability & Fit: Why are you a good candidate?)
        - |
            # Paragraph 5 (Conclusion: Reiterate interest and express gratitude)

    footer:
        # Closing
        closing: "Sincerely,"

        # Signature
        signature_name: "[Applicant's Full Name]"
```
The yaml file should be well-structured and easy to read.
Dont include any extra information or comments outside of the yaml structure. No even yaml comments.
All fields are optional, but if a field is not applicable, use null or an empty string.
The motivation letter should be persuasive, genuine, and tailored to the specific application.
The output should be in {language} language.

Information about the applicant:
{about_candidate}
Information about the program/scholarship/opportunity:
{other_info}

Yaml Output:"""

motivation_letter_prompt = PromptTemplate.from_template(motivation_letter_template)

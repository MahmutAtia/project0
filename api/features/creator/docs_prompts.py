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

Information  about candidate:
{about_candidate}
Information about the job and the company:
{company_and_job_info}

Yaml Output:"""

cover_letter_prompt =  PromptTemplate.from_template( cover_letter_template)


from typing import Dict, Any


class AIDraftingService:

    @classmethod
    def generate_outreach_draft(
        cls,
        template_type: str,  # outreach, invite, rejection, offer_followup
        candidate_name: str,
        job_title: str,
        recruiter_name: str
    ) -> Dict[str, str]:
        """Draft customized recruitment emails."""
        if template_type == "invite":
            subject = f"Interview invitation: {job_title} at SmartOnboard"
            body = (
                f"Hi {candidate_name},\n\n"
                f"We are impressed by your qualifications and would love to schedule a video conversation for the {job_title} role.\n\n"
                f"Please let us know your availability for next week.\n\n"
                f"Best regards,\n{recruiter_name}"
            )
        elif template_type == "rejection":
            subject = f"Application Update: {job_title} at SmartOnboard"
            body = (
                f"Hi {candidate_name},\n\n"
                f"Thank you for taking the time to apply and interview for the {job_title} position.\n\n"
                f"Unfortunately, we are proceeding with other candidates whose backgrounds more closely align with our current needs.\n\n"
                f"We wish you the best in your search.\n\n"
                f"Sincerely,\n{recruiter_name}"
            )
        elif template_type == "offer_followup":
            subject = f"Offer Status Update: {job_title} position"
            body = (
                f"Hi {candidate_name},\n\n"
                f"I wanted to follow up on the offer contract we sent over yesterday. Let me know if you have any questions.\n\n"
                f"Best,\n{recruiter_name}"
            )
        else:  # outreach
            subject = f"Sourcing outreach: {job_title} opportunity"
            body = (
                f"Hi {candidate_name},\n\n"
                f"I came across your profile and noticed your strong background. We are actively hiring for a {job_title} and thought you'd be a great fit.\n\n"
                f"Let me know if you'd be open to a brief call.\n\n"
                f"Best,\n{recruiter_name}"
            )

        return {
            "subject": subject,
            "body": body
        }

    @classmethod
    def generate_interview_briefing(
        cls,
        candidate_name: str,
        job_title: str,
        skills: str,
        match_score: float
    ) -> Dict[str, Any]:
        """Generate briefing packages for the interview panel."""
        return {
            "candidate_name": candidate_name,
            "briefing": (
                f"### Interview Briefing: {candidate_name} ({job_title})\n\n"
                f"**Match Score**: {match_score}% fit estimate.\n\n"
                f"**Focus Skills**: {skills}\n\n"
                f"**Suggested Interview Focus Areas**:\n"
                f"1. Probe deep-dive understanding of system concurrency designs.\n"
                f"2. Discuss prior team collaboration patterns and agile sprints.\n"
                f"3. Verify knowledge in cloud deployment structures."
            )
        }

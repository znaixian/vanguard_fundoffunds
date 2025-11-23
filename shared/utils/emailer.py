"""
Email Notifier
Sends structured email reports
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import yaml


class EmailNotifier:
    """Sends email notifications for fund calculations."""

    def __init__(self, config_path: str):
        """
        Initialize email notifier.

        Args:
            config_path: Path to email_config.yaml
        """
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Read password from separate file
        password_file = self.config['smtp']['password_file']
        with open(password_file) as f:
            self.password = f.read().strip()

    def send_daily_summary(
        self,
        date: str,
        results: List[Dict],
        attachments: List[Path] = None,
        s3_results: Dict = None
    ):
        """
        Send daily summary email.

        Args:
            date: Calculation date
            results: List of fund result dictionaries
            attachments: Optional list of file paths to attach
        """
        # Determine overall status
        statuses = [r['status'] for r in results]

        if all(s == 'SUCCESS' for s in statuses):
            status_prefix = "[SUCCESS]"
        elif all(s == 'FAILED' for s in statuses):
            status_prefix = "[FAILURE]"
        else:
            status_prefix = "[PARTIAL]"

        subject = f"{status_prefix} Fund Calculations {date}"

        # Build email body
        html_body = self._build_html_body(date, results, s3_results or {})

        # Get recipients based on status
        if status_prefix == "[SUCCESS]":
            recipients = self.config['recipients']['success']
        elif status_prefix == "[PARTIAL]":
            recipients = self.config['recipients']['partial']
        else:
            recipients = self.config['recipients']['failure']

        # Send email
        self._send_email(
            to=recipients,
            subject=subject,
            html_body=html_body,
            attachments=attachments or []
        )

        print(f"Summary email sent to: {', '.join(recipients)}")

    def _build_html_body(self, date: str, results: List[Dict], s3_results: Dict) -> str:
        """Build HTML email body with summary table."""
        # Build table rows
        rows = []
        for r in results:
            status_color = "green" if r['status'] == 'SUCCESS' else "red"
            status_icon = "SUCCESS" if r['status'] == 'SUCCESS' else "FAILED"

            runtime = f"{r.get('runtime', 0):.1f}s" if 'runtime' in r else "N/A"
            output = r.get('output_path', 'N/A')
            warnings = "<br>".join(r.get('warnings', [])) if r.get('warnings') else "None"
            error = r.get('error', '')

            rows.append(f"""
            <tr>
                <td>{r['fund']}</td>
                <td style="color: {status_color};">{status_icon}</td>
                <td>{runtime}</td>
                <td style="font-size: 10px;">{output}</td>
                <td>{warnings}</td>
                <td style="color: red;">{error}</td>
            </tr>
            """)

        # Build S3 upload section if available
        s3_section = ""
        if s3_results:
            s3_rows = []
            for fund_name, file_results in s3_results.items():
                successful = sum(1 for v in file_results.values() if v)
                total = len(file_results)
                s3_status = "SUCCESS" if successful == total else f"PARTIAL ({successful}/{total})"
                s3_color = "green" if successful == total else "orange"

                s3_rows.append(f"""
                <tr>
                    <td>{fund_name}</td>
                    <td style="color: {s3_color};">{s3_status}</td>
                    <td>{successful}/{total} files</td>
                </tr>
                """)

            s3_section = f"""
            <h3>AWS S3 Upload Status</h3>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr style="background-color: #e8f4f8;">
                    <th>Fund</th>
                    <th>Status</th>
                    <th>Files Uploaded</th>
                </tr>
                {''.join(s3_rows)}
            </table>
            <p style="font-size: 11px; color: gray;">
                Files uploaded to S3 are available in the cloud for backup and distribution.
            </p>
            """
        elif any(r['status'] == 'SUCCESS' for r in results):
            s3_section = """
            <h3>AWS S3 Upload Status</h3>
            <p style="color: gray;">S3 upload is currently disabled. To enable cloud backup, see config/aws_config.yaml</p>
            """

        html = f"""
        <html>
        <body>
            <h2>Fund Calculation Summary - {date}</h2>

            <table border="1" cellpadding="5" cellspacing="0">
                <tr style="background-color: #f0f0f0;">
                    <th>Fund</th>
                    <th>Status</th>
                    <th>Runtime</th>
                    <th>Output File</th>
                    <th>Warnings</th>
                    <th>Errors</th>
                </tr>
                {''.join(rows)}
            </table>

            {s3_section}

            <h3>Next Steps</h3>
            <ul>
                <li>Review warnings and reconciliation alerts</li>
                <li>Check log files for detailed execution trace</li>
                <li>Verify output files before distribution</li>
            </ul>

            <p style="color: gray; font-size: 11px;">
                This is an automated email from the Fund Calculation System.<br>
                Logs and output files available at: {Path.cwd()}
            </p>
        </body>
        </html>
        """

        return html

    def _send_email(self, to: List[str], subject: str, html_body: str, attachments: List[Path]):
        """Send email via SMTP with attachments."""
        msg = MIMEMultipart()
        msg['From'] = self.config['smtp']['username']
        msg['To'] = ', '.join(to)
        msg['Subject'] = subject

        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))

        # Attach files
        for file_path in attachments:
            if file_path.stat().st_size > self.config['attachments']['max_size_mb'] * 1024 * 1024:
                print(f"Skipping attachment {file_path.name}: exceeds max size")
                continue

            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={file_path.name}')
            msg.attach(part)

        # Send with timeout to prevent hanging
        try:
            with smtplib.SMTP(self.config['smtp']['server'], self.config['smtp']['port'], timeout=30) as server:
                if self.config['smtp']['use_tls']:
                    server.starttls()
                server.login(self.config['smtp']['username'], self.password)
                server.send_message(msg)
        except Exception as e:
            print(f"WARNING: Email send failed: {e}")
            print(f"Email details: to={to}, subject={subject}")
            raise  # Re-raise so caller knows email failed

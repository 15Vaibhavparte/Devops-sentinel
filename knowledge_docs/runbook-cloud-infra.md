# Runbook: Cloud Infrastructure & Networking

## Topic: SSH Connectivity Failure
- **Problem:** You are unable to connect to a cloud VM instance (e.g., AWS EC2, Azure VM) via SSH. Errors can be "Connection timed out" or "Connection refused".
- **Diagnosis & Resolution:**
  1. **Security Groups / Network Security Groups (NSGs):** This is the most common cause. Verify that the instance's security group has an inbound rule that allows traffic on **port 22** from **your current IP address**. A "Connection timed out" error often points to a restrictive firewall rule.
  2. **Instance State:** Check your cloud provider's console to ensure the VM is in a "running" or "healthy" state.
  3. **SSH Daemon Status:** If the connection is refused, it's possible the `sshd` service is not running on the VM itself. If you have another way to access the instance (like a serial console), check its status with `systemctl status sshd`.
  4. **Correct Key Pair:** Ensure you are using the correct private key (`.pem` or `.ppk` file) that corresponds to the public key configured for the instance.

## Topic: Cloud API Permission Denied (403 Error)
- **Problem:** An application or script fails when trying to access a cloud resource (like an S3 bucket, Azure Blob, or Google Cloud Storage) with a "Permission Denied" or "403 Forbidden" error.
- **Diagnosis & Resolution:**
  1. **Review IAM Policies:** Carefully inspect the IAM (Identity and Access Management) role or user policy attached to the entity making the request. The policy must explicitly grant permission for the specific action being attempted (e.g., `s3:GetObject`, `s3:PutObject`).
  2. **Resource-Based Policies:** Check if the resource itself has a policy that could be overriding the IAM policy. For example, an S3 bucket can have a "Bucket Policy" that explicitly denies access to certain principals, even if their IAM role allows it.
  3. **Credentials Configuration:** Verify that the application's environment is correctly configured with the credentials for the intended IAM role. For applications running on cloud instances, this is often handled automatically by an instance profile or managed identity. Ensure the instance has the correct role attached.
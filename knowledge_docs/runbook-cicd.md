# Runbook: CI/CD Pipeline Failures

## Topic: Build Stage Failure
- **Problem:** The pipeline fails during code compilation, dependency installation, or Docker image creation.
- **Diagnosis & Resolution:**
  1. **Dependency Resolution:** Check the build logs for "404 Not Found" errors from package managers (e.g., npm, Maven, Pip). This often indicates a private artifact repository is down or credentials are missing. Verify network connectivity from the build agent to the repository.
  2. **Failed Tests:** If the build fails at the "test" step, analyze the test results. A single failing unit test or integration test can (and should) fail the entire build. Run the tests locally to replicate the issue.
  3. **Docker Build Errors:** If `docker build` fails, look for errors like "COPY failed: no such file or directory," which means the path to a file in your Dockerfile is incorrect. If it fails on a command like `RUN apt-get install`, it could be a transient network issue or a problem with the base image's repositories.

## Topic: Deployment Stage Failure
- **Problem:** The pipeline successfully builds and tests the artifact, but fails when deploying it to an environment like Kubernetes or a cloud provider.
- **Diagnosis & Resolution:**
  1. **Authentication & Authorization:** Check the deployment logs for "401 Unauthorized" or "403 Forbidden" errors. This means the CI/CD pipeline's service principal or role does not have the necessary IAM permissions to deploy to the target environment (e.g., permission to create pods in a Kubernetes cluster, or to update an AWS Lambda function).
  2. **Resource Quotas:** Look for errors indicating resource quotas have been exceeded. Cloud environments have limits on CPUs, memory, and the number of services you can create. You may need to request a quota increase or clean up old, unused resources.
  3. **Post-Deployment Health Check Failure:** The deployment itself might succeed, but the application may fail to start correctly. This will cause the CD tool (like ArgoCD or Spinnaker) to roll back the deployment. In this case, you must investigate the application's logs using the other runbooks (e.g., the Kubernetes `CrashLoopBackOff` runbook).
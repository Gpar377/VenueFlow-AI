# Google Cloud Service Account Setup Guide

To enable automated deployment for VenueFlow AI via GitHub Actions, follow these steps to configure your Service Account.

## 1. Create Service Account
Navigate to **IAM & Admin > Service Accounts** and click **CREATE SERVICE ACCOUNT**.
- **Name**: `github-actions-deploy`
- **ID**: `github-actions-deploy`

## 2. Grant Permissions (CRITICAL)
In Step 2 (Grant this service account access to project), add the following roles:
- **Cloud Run Admin**: Allows deploying and managing Cloud Run services.
- **Cloud Build Editor**: Required to build the Docker image in the cloud.
- **Artifact Registry Administrator**: Allows pushing the container image to the registry.
- **Service Account User**: Allows the deployment to "act as" the service account.

## 3. Users Access (Optional)
In Step 3, you can leave everything blank and click **DONE**.

## 4. Generate JSON Key
1.  In the list of service accounts, click on the one you just created.
2.  Go to the **KEYS** tab.
3.  Click **ADD KEY > Create new key**.
4.  Select **JSON** and click **CREATE**.
5.  A file will download to your computer. **Copy the entire contents** of this file.

## 5. Configure GitHub
In your GitHub repo, go to **Settings > Secrets and variables > Actions**:
1.  Add `GCP_SA_KEY`: Paste the JSON content here.
2.  Add `GEMINI_API_KEY`: Your Gemini API Key.
3.  Add `GCP_PROJECT_ID`: `gen-lang-client-0302220586`

Once you push code to `main`, GitHub will automatically deploy VenueFlow AI!

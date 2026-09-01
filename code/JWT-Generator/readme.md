# Online JWT Generator

The `makeToken.html` file is a simple utility that can be used to generate static JSON Web Tokens (JWTs) using the **Tenant ID** and **Client Secret** from your SAS Customer Intelligence 360 tenant.

For the official instructions and additional information, refer to the [SAS Customer Intelligence 360 documentation](https://go.documentation.sas.com/doc/en/cintcdc/production.a/cintag/ext-auth-tokens-static-jwt.htm).

## How to Use

### Option 1: Use the Online Version

1. Open the [Online JWT Generator](https://htmlpreview.github.io/?https://github.com/sascommunities/ci360-launchpad/blob/main/code/JWT-Generator/makeToken.html).
2. Enter your **Tenant ID** and **Client Secret**.
3. Click **Submit** to generate the JWT.

### Option 2: Run the HTML File Locally

1. Download the [`makeToken.html`](makeToken.html) file to your local machine.
2. Open the HTML file in a web browser.
3. Enter your **Tenant ID** and **Client Secret**.
4. Click **Submit** to generate the JWT.

## ⚠️ Important Notice

This utility is provided **for training and demonstration purposes only**. It is **not intended for production use**.

Do not share your **Client Secret** or generated JWTs with others. Use appropriate security practices when handling authentication credentials.

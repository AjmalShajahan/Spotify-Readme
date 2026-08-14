<div align="center">
  <img src="assets/spotify.svg" width="100" align="center">
  <h1>Spotify Readme</h1>

  [![Issues](https://img.shields.io/github/issues/AjmalShajahan/Spotify-Readme?style=for-the-badge)](https://github.com/AjmalShajahan/Spotify-Readme/issues)
  [![Forks](https://img.shields.io/github/forks/AjmalShajahan/Spotify-Readme?style=for-the-badge)](https://github.com/AjmalShajahan/Spotify-Readme/network/members)
  [![Stars](https://img.shields.io/github/stars/AjmalShajahan/Spotify-Readme?style=for-the-badge)](https://github.com/AjmalShajahan/Spotify-Readme/stargazers)

</div>

<p align="center">
  A dynamic, customizable, and real-time Spotify now-playing widget for your README files that syncs with the song you’re currently playing. If you're not currently playing a song, it'll display one of your recent songs! Feel free to ask for help or make any PRs/issues/suggestions 😄
</p>

<p align="center">
  Maintained by <a href="https://github.com/AjmalShajahan">Ajmal Shajahan</a> · Forked from <a href="https://github.com/tthn0/Spotify-Readme">tthn0/Spotify-Readme</a> · Inspired by <a href="https://github.com/novatorem/novatorem">novatorem</a>
</p>

<p align="center">
  This repository is a modified fork maintained by Ajmal Shajahan since 2021. It includes contributions from the upstream project and other contributors and remains licensed under the <a href="LICENSE">GNU General Public License v3.0</a>.
</p>

## Previews

#### Default
```
/api
```
![Preview](https://ajmal-spotify-readme.vercel.app/api)

#### Spinning CD Effect
```
/api?spin=true
```
![Preview](https://ajmal-spotify-readme.vercel.app/api?spin=true)

#### Include Scan Code
```
/api?scan=true
```
![Preview](https://ajmal-spotify-readme.vercel.app/api?scan=true)

#### Rainbow Equalizer
```
/api?rainbow=true
```
![Preview](https://ajmal-spotify-readme.vercel.app/api?rainbow=true)

#### Dark Theme
```
/api?theme=dark
```
![Preview](https://ajmal-spotify-readme.vercel.app/api?theme=dark)

## Setup/Deployment

#### 1. Spotify's API 🎶

* Head over to <a href="https://developer.spotify.com/dashboard/">Spotify for Developers</a>.
  * For Spotify Development Mode apps, the app owner now needs an active Spotify Premium subscription. New Development Mode apps are also limited to 1 Client ID per developer and 5 users per app.
  * Accept the Terms of Service if necessary.
  * Verify your email address if you haven't done so already.
  * Click on the **Create app** button.
    * In the **App name** & **App description** fields, you may put whatever you want.
    * In the **Redirect URI** field, add `http://127.0.0.1:80/callback/`.
    * Agree with Spotify's TOS and click **Save**.
  * Click on the **Settings** button.
  * Take note of the **Client ID** & **Client Secret**.

#### 2. Get a Refresh Token 🛠️

```
https://accounts.spotify.com/authorize?client_id={CLIENT_ID}&response_type=code&scope=user-read-currently-playing%20user-read-recently-played&redirect_uri=http://127.0.0.1:80/callback/
```

* Copy and paste the above link into your browser.
  * Replace `{CLIENT_ID}` with the **Client ID** you got from your Spotify application.
  * Visit the URL.
    * Log in if you're not already signed in.
    * Click **Agree**.
* After you get redirected to a blank page, copy the `code` value from the browser URL. It should look like `http://127.0.0.1:80/callback/?code={CODE}`.
* In a local terminal, exchange the authorization code for tokens. Replace `{CLIENT_ID}` and `{CODE}`, then enter the Client Secret when `curl` prompts for a password. Never paste your Client Secret into a website, command, or Git commit.

  ```bash
  curl --request POST \
    --url https://accounts.spotify.com/api/token \
    --user "{CLIENT_ID}" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=authorization_code" \
    --data-urlencode "code={CODE}" \
    --data-urlencode "redirect_uri=http://127.0.0.1:80/callback/"
  ```

* The JSON response includes a `refresh_token`. Store it securely for the Vercel configuration step.

#### 3. Host on Vercel 🌀

* Fork this repository.
* Head over to <a href="https://vercel.com">Vercel</a> and create an account if you don't already have one.
  * Add a new project.
    * Link your GitHub account if you haven't done so already.
    * Make sure Vercel has access to the forked repository.
    * Import the forked repository into your project.
      * Give it a meaningful project name.
      * Keep the default options for the other settings.
      * Add the following environment variables along with their appropriate values:
        * `CLIENT_ID` ⇒ `{CLIENT_ID}`.
        * `CLIENT_SECRET` ⇒ `{CLIENT_SECRET}`.
        * `REFRESH_TOKEN` ⇒ `{REFRESH_TOKEN}`.
      * Click **Deploy**.
      * Click **Continue to Dashboard**.
        * Find the **Domains** field and take note of the URL.
          * Example: `{PROJECT_NAME}.vercel.app`.

#### 4. Add to your GitHub 🚀

* In any markdown file, add the following (replace `{PROJECT_NAME}` with the name you gave your Vercel project):

  ```html
  <a href="https://{PROJECT_NAME}.vercel.app/api/play">
    <img src="https://{PROJECT_NAME}.vercel.app/api" alt="Current Spotify Song">
  </a>

  <a href="https://github.com/tthn0/Spotify-Readme">Original Source</a>
  ```

* Please keep the original source link to credit the project creator and help other users find it.

## Customization

<p>
  To customize the widget, add query parameters to the endpoint. There are many possible combinations. If you're on mobile and have a small screen, use a desktop browser or zoom out.
</p>

| Parameter | Default | Values          |
| :-------- | :------ | :-------------- |
| `spin`    | `false` | `false`, `true` |
| `scan`    | `false` | `false`, `true` |
| `theme`   | `light` | `light`, `dark` |
| `rainbow` | `false` | `false`, `true` |

## Keep Your Fork Up To Date

You can keep your fork, and thus your private Vercel instance up to date with the upstream using GitHub's <a href="https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork">Sync Fork button</a>.

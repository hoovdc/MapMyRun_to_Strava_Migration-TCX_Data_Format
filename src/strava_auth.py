import logging
import os
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import json

from dotenv import load_dotenv
from stravalib.client import Client

load_dotenv(dotenv_path='config/.env')
logger = logging.getLogger(__name__)

TOKEN_FILE = 'config/strava_token.json'


class StravaAuthenticator:
    """
    Handles the Strava OAuth2 authentication process, including token storage and refresh.
    """
    def __init__(self, client_id: str, client_secret: str):
        """
        Initializes the authenticator with Strava API credentials.

        Args:
            client_id (str): The Strava application's Client ID.
            client_secret (str): The Strava application's Client Secret.
        """
        if not client_id or not client_secret:
            raise ValueError("Strava client_id and client_secret must be provided.")
        
        self.client = Client()
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None

        self._load_token()

    def _save_token(self, token_response: dict):
        """Saves the token data to a file."""
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_response, f)
        logger.info(f"Token data saved to {TOKEN_FILE}")

    def _load_token(self):
        """Loads token data from a file if it exists."""
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            self.access_token = token_data['access_token']
            self.refresh_token = token_data['refresh_token']
            self.expires_at = token_data['expires_at']
            self.client.access_token = self.access_token
            logger.info(f"Token data loaded from {TOKEN_FILE}")

    def get_authorization_url(self, redirect_uri: str) -> str:
        """
        Generates the Strava OAuth authorization URL.

        Args:
            redirect_uri (str): The URI to redirect to after authorization.

        Returns:
            str: The full authorization URL.
        """
        return self.client.authorization_url(
            client_id=self.client_id,
            redirect_uri=redirect_uri,
            scope=['read_all', 'activity:write', 'activity:read_all']
        )

    def exchange_code_for_token(self, code: str) -> dict:
        """
        Exchanges an authorization code for an access token.

        Args:
            code (str): The authorization code from Strava's redirect.

        Returns:
            dict: A dictionary containing the token information.
        """
        try:
            token_response = self.client.exchange_code_for_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=code
            )
            self.access_token = token_response['access_token']
            self.refresh_token = token_response['refresh_token']
            self.expires_at = token_response['expires_at']
            
            logger.info("Successfully exchanged authorization code for access token.")
            return token_response
        except Exception as e:
            logger.error(f"Failed to exchange authorization code for token: {e}")
            raise

    def refresh_access_token(self) -> dict:
        """
        Refreshes an expired access token using the stored refresh token.
        """
        if not self.refresh_token:
            raise Exception("No refresh token available. Please re-authenticate.")

        try:
            new_token = self.client.refresh_access_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=self.refresh_token
            )
            self._save_token(new_token)
            self.access_token = new_token['access_token']
            self.refresh_token = new_token['refresh_token']
            self.expires_at = new_token['expires_at']
            self.client.access_token = self.access_token
            logger.info("Successfully refreshed access token.")
            return new_token
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise

    def _start_local_server(self, port: int = 8000) -> str:
        """
        Starts a temporary local web server to capture the OAuth redirect.

        Args:
            port (int): The port on which to run the server.

        Returns:
            str: The authorization code extracted from the redirect URI.
        """
        auth_code = None

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal auth_code
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                auth_code = query_params.get('code', [None])[0]

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                if auth_code:
                    self.wfile.write(b"<html><body><h1>Authentication successful!</h1>"
                                     b"<p>You can close this window.</p></body></html>")
                else:
                    self.wfile.write(b"<html><body><h1>Authentication failed.</h1>"
                                     b"<p>Please try again.</p></body></html>")

        with HTTPServer(('localhost', port), OAuthCallbackHandler) as httpd:
            logger.info(f"Local server started on port {port}. Waiting for authorization code...")
            httpd.handle_request()  # Serve one request and exit

        if not auth_code:
            raise Exception("Could not capture authorization code from Strava redirect.")
        
        return auth_code

    def authenticate(self, port: int = 8000) -> Client:
        """
        Orchestrates the full authentication flow.

        Tries to load a token, refreshes if expired, and only
        initiates the browser flow if no valid token is found.

        Args:
            port (int): The port for the local OAuth redirect server.

        Returns:
            A fully authenticated stravalib Client.
        """
        if self.expires_at and time.time() < self.expires_at:
            logger.info("Access token is valid.")
            self.client.access_token = self.access_token
            return self.client
        
        if self.refresh_token:
            logger.info("Access token has expired, attempting to refresh.")
            try:
                self.refresh_access_token()
                self.client.access_token = self.access_token
                return self.client
            except Exception as e:
                logger.warning(f"Could not refresh token: {e}. Starting full re-authentication.")

        # --- Full OAuth Flow ---
        redirect_uri = f'http://localhost:{port}/'
        auth_url = self.get_authorization_url(redirect_uri)
        
        print("\n--- Strava Authentication Required ---")
        print("Your browser will now open to authorize this application.")
        print("If it does not, please open this URL manually:")
        print(f"  {auth_url}")
        
        webbrowser.open(auth_url)

        auth_code = self._start_local_server(port)
        
        token_response = self.exchange_code_for_token(auth_code)
        self._save_token(token_response)
        
        self.client.access_token = self.access_token
        logger.info("Strava authentication successful.")
        return self.client 
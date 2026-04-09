import requests
import json

def get_appid():
    with open('config.json', 'r') as file:
        config = json.load(file)
    appid = config['app_id']
    return appid



def get_appsecret():
    with open('config.json', 'r') as file:
        config = json.load(file)
    appsecret = config['app_secret']
    return appsecret


def get_access_token(app_id, app_secret):
    url = "https://openapi.lingxing.com/api/auth-server/oauth/access-token"

    # Prepare the data payload
    data = {
        "appId": app_id,
        "appSecret": app_secret
    }

    # Set the headers (Content-Type)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        # Make the POST request to fetch the token
        response = requests.post(url, data=data, headers=headers)

        # # Print the response status and body for debugging
        # print("Response Status Code:", response.status_code)
        # print("Response Text:", response.text)

        # Check if the request was successful
        if response.status_code == 200:
            try:
                response_data = response.json()

                # Check if we have the 'access_token' in the response
                if 'data' in response_data and 'access_token' in response_data['data']:
                    return response_data['data']['access_token']
                else:
                    raise Exception(f"Error: {response_data.get('msg', 'Unknown error')}")
            except ValueError:
                raise Exception("Error parsing JSON response.")
        else:
            raise Exception(f"Request failed with status code {response.status_code}")

    except requests.exceptions.RequestException as e:
        # Handle any request exceptions
        raise Exception(f"Request error: {str(e)}")


# if __name__ == '__main__':
#
#     # Example usage:
#     app_id = 'ak_QDCz6IZK1BX8A'  # Replace with your actual appId
#     app_secret = 'TufqJk7LjGOzlQ82URp2kg=='  # Replace with your actual appSecret
#
#     try:
#         token = get_access_token(app_id, app_secret)
#         print(f"Access Token: {token}")
#     except Exception as e:
#         print(f"Error: {str(e)}")
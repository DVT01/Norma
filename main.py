#  Automatically download images and post then to reddit

from datetime import datetime, timedelta
from os.path import join, isfile
from bs4 import BeautifulSoup
import concurrent.futures
import requests
import praw
import time


image_directory = r'C:\Users\DVT\My Files\Projects\Norma\Images'


def get_images():

    # Go to wallpaperscraft front page while sorting by ratings and 4k
    wallpapers_source = requests.get(f'https://wallpaperscraft.com/all/ratings/3840x2160/page{current_page}').text
    wallpapers_soup = BeautifulSoup(wallpapers_source, 'lxml')

    print('Went to wallpaperscraft')

    # Get the list of wallpapers
    wallpaper_list = wallpapers_soup.find('ul', 'wallpapers__list')
    wallpapers_page = [
        'https://wallpaperscraft.com' + str(wallpaper.a['href'])
        for wallpaper in wallpaper_list.find_all('li')
    ]

    print('Got list of wallpapers')

    # Get download link of every picture
    wallpaper_download_link = list()
    for image_page in wallpapers_page:
        image_source = requests.get(image_page).text
        image_soup = BeautifulSoup(image_source, 'lxml')
        wallpaper_download_link.append(image_soup.find('a', 'gui-button gui-button_full-height')['href'])

    print('Finished getting links of imagess')

    return wallpapers_page, wallpaper_download_link


def download_image(image_url):
    image_name = image_url.split('/')[-1]
    image_path = join(image_directory, image_name)

    if isfile(image_path):
        print(f'Skipping {image_name} download.')
        return

    print(f'Downloading {image_name}')

    with open(image_path, 'wb') as image:
        image.write(requests.get(image_url).content)
        print(f'{image_name} was downloaded!')


def get_image_title(image_page):

    # Go to wallpaper page
    wallpaper_page = requests.get(image_page).text
    wallpaper_soup = BeautifulSoup(wallpaper_page, 'lxml')

    # Get title of wallpaper
    wallpaper_header = wallpaper_soup.find('h1', 'gui-h2 gui-heading').text
    wallpaper_parse = wallpaper_header.replace('Download 3840x2160 ', '').replace('background 4k uhd 16:9', '').split(', ')

    return (wallpaper_parse[0] + ' ' + wallpaper_parse[1]).strip().capitalize()


def complete_process_to_get_wallpapers():

    wallpapers_page, wallpapers_download_link = get_images()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(download_image, wallpapers_download_link)

    print(f'Took {(time.time() - start):.2f} seconds to search and download images.')

    i = dict()
    for image_page, image_download in zip(wallpapers_page, wallpapers_download_link):
        image_name = image_download.split('/')[-1]
        image_path = join(image_directory, image_name)

        i[get_image_title(image_page)] = [image_path, image_download]

    return i


def post_picture(picture_title, picture_directory, download_link):

    for post_id in user.submissions.new(limit=None):

        post = praw.reddit.models.Submission(
            reddit=reddit_client,
            id=post_id
        )

        if picture_title in post.title:
            print(f'{picture_title} already posted.')
            return -1

    print(f'Posting {picture_title}.')

    picture_post = wallpaper_subreddit.submit_image(
       title=f'{picture_title} [3840x2160]',
       image_path=picture_directory
    )

    picture_post_as_submission = praw.reddit.models.Submission(
        reddit=reddit_client,
        id=picture_post.id
    )

    picture_post_as_submission.reply(f'[Source]({download_link})')

    print(f'{picture_title} posted.')


if __name__ == '__main__':

    start = time.time()
    current_page = 0

    reddit_client = praw.Reddit(
        client_id="ABkB7KIufNDtRA",
        client_secret="vtXU6L3bKvji-Dsr9evOn35Vqq4",
        user_agent="Python:Norma:v20.5.03 (by /u/DVT01)",
        password="<your-reddit-password>",
        username="<your-reddit-username>"
    )

    user = reddit_client.user.me()

    if user != 'DVT01':
        print('ERROR!')
        exit()

    reddit_client.validate_on_submit = True

    wallpaper_subreddit = reddit_client.subreddit('wallpaper')

    while True:
        current_page += 1
        print(f'On page {current_page} of wallpaperscraft.')
        images = complete_process_to_get_wallpapers()

        for title, attributes in images.items():
            p = post_picture(title, attributes[0], attributes[1])

            if p == -1:
                continue

            print(f'Started waiting at {datetime.now().strftime("%H:%M")}, should post at {(datetime.now() + timedelta(seconds=1800)).strftime("%H:%M")}')
            time.sleep(1800)

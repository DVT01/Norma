#  Automatically download images and post then to reddit

from datetime import datetime, timedelta
from os.path import join, isfile
from bs4 import BeautifulSoup
import concurrent.futures
import requests
import praw
import time


def get_images(wallpapers_link, post_type):

    # Go to wallpaperscraft front page while sorting by ratings and 4k
    wallpapers_source = requests.get(wallpapers_link).text
    wallpapers_soup = BeautifulSoup(wallpapers_source, 'lxml')

    print(f'{post_type} -> Went to wallpaperscraft')

    # Get the list of wallpapers
    wallpaper_list = wallpapers_soup.find('ul', 'wallpapers__list')
    wallpapers_page = [
        'https://wallpaperscraft.com' + str(wallpaper.a['href'])
        for wallpaper in wallpaper_list.find_all('li')
    ]

    print(f'{post_type} -> Got list of wallpapers')

    wallpaper_download_link = list()
    wallpaper_source = list()

    for image_page in wallpapers_page:
        image_page_soup = BeautifulSoup(requests.get(image_page).text, 'lxml')

        # Get download link of every picture
        wallpaper_download_link.append(image_page_soup.find('a', 'gui-button gui-button_full-height')['href'])

        # Get the source for each wallpaper
        try:
            wallpaper_source.append([
                image_page_soup.find_all('div', 'author__row')[0].text.replace('Author: ', ''),
                image_page_soup.find('a', 'author__link')['href'],
            ])
        except TypeError:
            wallpaper_source.append([
                None,
                None,
            ])

    print(f'{post_type} -> Finished getting links of images')

    return wallpapers_page, wallpaper_download_link, wallpaper_source


def download_image(image_url, download_directory, post_type):
    image_name = image_url.split('/')[-1]
    image_path = join(download_directory, image_name)

    if isfile(image_path):
        print(f'{post_type} -> Skipping {image_name} download.')
        return

    print(f'{post_type} -> Downloading {image_name}')

    with open(image_path, 'wb') as image:
        image.write(requests.get(image_url).content)
        print(f'{post_type} -> {image_name} was downloaded!')


def get_image_title(image_page, resolution):

    # Get title of wallpaper
    wallpaper_header = BeautifulSoup(requests.get(image_page).text, 'lxml').find('h1', 'gui-h2 gui-heading').text

    wallpaper_parse = wallpaper_header.replace(f'Download {resolution} ', '').split(', ')

    return (wallpaper_parse[0] + ' ' + wallpaper_parse[1]).strip().capitalize()


def complete_process_to_get_wallpapers(wallpapers_link, picture_directory, post_type):

    wallpapers_page, wallpapers_download_link, wallpaper_source = get_images(wallpapers_link, post_type)

    with concurrent.futures.ThreadPoolExecutor() as _executor:
        for wallpaper in wallpapers_download_link:
            _executor.submit(download_image, wallpaper, picture_directory, post_type)

    images = dict()
    for image_page, image_download, image_source in zip(wallpapers_page, wallpapers_download_link, wallpaper_source):
        resolution = image_page.split('/')[-1]

        images[get_image_title(image_page, resolution)] = [
            join(picture_directory, image_download.split('/')[-1]),
            image_download, image_source[0],
            image_source[1], resolution,
        ]

    return images


def post_picture(title, directory, download_link, subreddit, author, author_link, resolution, post_type):

    for user_post in user_submissions:
        if title in user_post.title and subreddit == user_post.subreddit:
            print(f'{title} already posted.')
            return -1

    print(f'{post_type} -> Posting {title}.')

    if author is None:
        post_title = f'{title} [{resolution}]'
        post_reply = f'[Download Link]({download_link})'
    else:
        post_title = f'{title} by {author} [{resolution}]'
        post_reply = f'[{author}]({author_link})\n\n[Download Link]({download_link})'

    picture_post = subreddit.submit_image(
       title=post_title,
       image_path=directory
    )

    praw.reddit.models.Submission(
        reddit=reddit_client,
        id=picture_post.id
    ).reply(post_reply)

    print(f'{post_type} -> {post_title} posted to {subreddit}.')


def complete_process(wallpapers_link, subreddit, folder, post_type):
    wallpaper_subreddit = reddit_client.subreddit(subreddit)
    current_page = 0

    while True:
        current_page += 1
        wallpapers_link = f'{wallpapers_link}{current_page}'

        print(f'{post_type} -> On page {current_page} of wallpaperscraft.')

        start = time.time()

        images = complete_process_to_get_wallpapers(wallpapers_link, folder, post_type)

        print(f'{post_type} -> Took {(time.time() - start):.2f} seconds to finish complete process to get wallpapers.')

        for title, attributes in images.items():
            time_check()

            if post_picture(
                title,
                attributes[0], attributes[1],
                wallpaper_subreddit,
                attributes[2], attributes[3],
                attributes[4], post_type,
            ) == -1:
                continue

            now = datetime.now()
            _calculated_time = (now + timedelta(seconds=1800)).strftime("%H:%M")

            print(f'{post_type} -> Started waiting at {now.strftime("%H:%M")}, should post at {_calculated_time}')
            time.sleep(1800)


def time_check():
    not_within_time = True

    while not_within_time:
        now = datetime.now()
        now_formatted = now.strftime("%d%b%Y - %H:%M").upper()
        start_time = datetime(now.year, now.month, now.day, hour=6)
        end_time = datetime(now.year, now.month, now.day, hour=20)

        if start_time < now < end_time:
            not_within_time = False
            print(f'{now_formatted} within time.')
        else:
            print(f'{now_formatted} not within time.')
            time.sleep(60)


if __name__ == '__main__':

    reddit_client = praw.Reddit(
        client_id="ABkB7KIufNDtRA",
        client_secret="vtXU6L3bKvji-Dsr9evOn35Vqq4",
        user_agent="Python:Norma:v20.5.03 (by /u/DVT01)",
        username="<your-reddit-username>",
        password="<your-reddit-password>",
    )

    reddit_client.validate_on_submit = True
    user = reddit_client.user.me()

    # Make sure we got connection
    if user != '<your-reddit-username>':
        print('ERROR!')
        exit()

    # Scan and use the user submissions necessary
    st_time = time.time()

    user_submissions = list()
    for post_id in user.submissions.new(limit=None):

        post = praw.reddit.models.Submission(
            reddit=reddit_client,
            id=post_id
        )

        if post.subreddit in ['wallpaper', 'iWallpaper']:
            user_submissions.append(post)

    print(f'Took {time.time() - st_time} seconds to sort all the user submissions.')

    # Desktop wallpapers
    desktop_subreddit = 'wallpaper'
    desktop_download_directory = r'C:\Users\DVT\My Files\Projects\Norma (Reddit)\Desktop Images'
    desktop_wallpapers_link = 'https://wallpaperscraft.com/all/ratings/3840x2160/page'
    desktop_type = 'Desktop Photo'

    # Phone wallpapers
    phone_subreddit = 'iWallpaper'
    phone_download_directory = r'C:\Users\DVT\My Files\Projects\Norma (Reddit)\Phone Images'
    phone_wallpapers_link = 'https://wallpaperscraft.com/all/ratings/2160x3840/page'
    phone_type = 'Phone Photo'

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(
            complete_process,

            desktop_wallpapers_link,
            desktop_subreddit,
            desktop_download_directory,
            desktop_type,
        )

        executor.submit(
            complete_process,

            phone_wallpapers_link,
            phone_subreddit,
            phone_download_directory,
            phone_type,
        )

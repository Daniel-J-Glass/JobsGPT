# JobsGPT

## What is it?

This is a python script that will automatically apply to job postings.

## How do I use it?

1. Fill in the config.yaml
2. Set up the cover letter
3. Set up the resume
4. Set up the job postings you want to apply to
5. Fill in config.json and summarizer_config.json
6. Navigate to the LinkedIn-Easy-Apply-Bot directory and run the script (You need to click submit on each job application by default)
7. Fill in the <user>-Details.txt as questions come up that the bot doesn't know
8. Once the bot is accurate enough, you can disable the "test" variable in easyapplybot.py.

## WARNING

Please make sure your bot is accurate before applying to jobs. I've included my details file to show just how much it needs to not lie!!!

## How does it work?

The script will scrape the job posting website for the job posting URL, and then it will use the information from the job posting to automatically generate a cover letter with OpenAI api, then will go through the job listing and answer the job questions based on resume and custom details using OpenAI api as well.

## TODO

- [ ] Improve honesty through better prompting
- [ ] Skip job if job description isn't relevant
- [ ] Code refactoring and cleanup, this was just to get it working without rewriting the auto-apply script
- [ ] Centralize config files
- [ ] Workday application functionality
- [ ] Improved flexibility using GPT3 A* search
- [ ] GUI maybe???

## How can I contribute?

If you are a developer, feel free to contribute to the project. If you are a user, please file an issue or submit a pull request with the changes you would like to see.

## What is the license?

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## How can I contact you?

You can email me at danieljglass1@gmail.com

## Credits

Thanks to https://github.com/nicolomantini/LinkedIn-Easy-Apply-Bot for the code foundation.

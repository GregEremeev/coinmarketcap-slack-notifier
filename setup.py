from setuptools import setup, find_packages


requirements = [r.strip() for r in open('requirements.txt').readlines() if '#' not in r]


setup(
    name='coinmarketcap-slack-notifier',
    author='Greg Eremeev',
    author_email='gregory.eremeev@gmail.com',
    version='0.1.0',
    license='BSD',
    url='https://github.com/GregEremeev/coinmarketcap-slack-notifier',
    install_requires=requirements,
    description='Application which sends notifications about changes on coinmarketcap.com to the slack channel',
    packages=find_packages(),
    extras_require={'dev': ['ipdb==0.10.3']},
    classifiers=['Programming Language :: Python :: 2.7'],
    zip_safe=False,
    include_package_data=True
)

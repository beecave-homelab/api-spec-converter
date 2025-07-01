from setuptools import setup, find_packages

setup(
    name='api-spec-converter-py',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'click',
        'requests',
        'PyYAML',
        'jsonschema',
        # Add other dependencies here as they are identified
    ],
    entry_points={
        'console_scripts': [
            'api-spec-converter-py = api_spec_converter_py.cli:main',
        ],
    },
    author='Jules',
    author_email='', # TODO: Add email
    description='A Python port of the api-spec-converter utility.',
    long_description=open('README.md').read() if hasattr(__builtins__, 'open') and __import__('os').path.exists('README.md') else '', # Protects against errors during build if README.md doesn't exist yet
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/api-spec-converter-py',  # TODO: Update with actual URL
    license='MIT', # Assuming MIT license based on the original project
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)

from sandbox_scripts.environment.teardown.teardown_script import EnvironmentTeardown
from sandbox_scripts.environment.teardown.teardown_resources import EnvironmentTeardownResources

def main():
    EnvironmentTeardown().execute()
    EnvironmentTeardownResources().execute()

if __name__ == "__main__":
    main()

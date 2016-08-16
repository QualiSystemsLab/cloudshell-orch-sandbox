from sandbox_scripts.environment.setup.setup_script import EnvironmentSetup
from sandbox_scripts.environment.setup.setup_resources import EnvironmentSetupResources


def main():
    EnvironmentSetup().execute()
    EnvironmentSetupResources().execute()

if __name__ == "__main__":
    main()

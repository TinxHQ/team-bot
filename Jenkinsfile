pipeline {

  agent any

  triggers {
    cron('30 15 * * 1-5')
  }

  environment {
    MATTERMOST_HOOK_URL = credentials("mattermost-teambot-hook")
  }

  stages {

    stage ('Prepare') {
      steps {
        script {
          currentBuild.description = "Teambot run for the day"
        }
        checkout scm
      }
    }

    stage ('Run') {
      steps {
        sh 'python3 ./agenda.py planning.yaml "$MATTERMOST_HOOK_URL" dev-daily-scrum'
      }
    }
  }

  post {
    failure {
      mattermostSend color: "danger", message: "Teambot [failed :nuke:](${BUILD_URL}/console)"
    }
  }
}

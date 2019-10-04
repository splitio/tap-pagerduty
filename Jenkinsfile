#!/usr/bin/env groovy

pipeline {
    agent any

    triggers {
      cron('H * * * *') // run every hour
    }

    options {
      buildDiscarder(logRotator(daysToKeepStr: '2'))
    }

    environment {
      SF_ROLE="SYSADMIN"
      SF_DATABASE="SPLIT"
      SF_WAREHOUSE="COMPUTE_WH"
      SF_CRED=credentials("SNOWFLAKE")
      SF_ACCOUNT="bv23770.us-east-1"

      // State File
      PAGERDUTY_STATE="./states/pagerduty.json"

      // Python Enviroments
      VENV_PAGERDUTY="venv/tap-pagerduty"
      VENV_SF="venv/target-snowflake"

    }

    stages {

        stage('Create States directory') {
          steps {
            sh "mkdir -p ./states"
          }
        } // Stage States Directory

        stage('Create Venvs') {
          parallel {
            stage('Venv Pagerduty') {
              environment {
                SOURCE_INSTALL='.[dev]'
                FLAG="-e"
              }
              steps {
                sh './createVenv.sh "${VENV_PAGERDUTY}" "${SOURCE_INSTALL}" "${FLAG}"'
              }
            }// stage Venv Pagerduty
            stage('Venv Snowflake') {
              environment {
                SOURCE_INSTALL='git+https://gitlab.com/meltano/target-snowflake.git@master#egg=target-snowflake'
                FLAG="-e"
              }
              steps {
                sh './createVenv.sh "${VENV_SF}" "${SOURCE_INSTALL}" "${FLAG}"'
              }
            } // Stage Venv Snowflake
            stage('State Pagerduty'){
              steps{
                setState("${PAGERDUTY_STATE}")
              }
            } // stage State Pagerduty
          } // Parallel
        } // Stage Create Venv

        stage('Run Tap-pagerduty'){
          environment{
            PAGERDUTY_START_DATE="2017-01-01"
            PAGERDUTY_TOKEN=credentials('PAGERDUTY_TOKEN')
            SF_SCHEMA="PAGERDUTY"
            SF_CONFIG_FILE="config-snoflake-pagerduty.json"
            TAP_OUTPUT="tap-pagerduty-output.json"
            STDERRFILE="stderr_pager.out"
          }
          steps{
            script{
              sh(returnStdout: false, script: 'set -euo pipefail')
              sh(returnStdout: false, script: 'envsubst < config-pagerduty.json.tpl > config-pagerduty.json')
              sh(returnStdout: false, script: 'envsubst < config-snowflake.json.tpl > "${SF_CONFIG_FILE}"')
              status=sh(returnStatus: true, script: '${VENV_PAGERDUTY}/bin/tap-pagerduty -c config-pagerduty.json --catalog pagerduty-properties.json -s "${PAGERDUTY_STATE}" > "${TAP_OUTPUT}"  2>"${STDERRFILE}"')
              catchError(status, "Tap-pagerduty", "Failed to collect data.", "${STDERRFILE}")
              status=sh(returnStdout: false, script:'echo -e "\n" >>  ${PAGERDUTY_STATE}')
              status=sh(returnStatus: true, script: 'cat ${TAP_OUTPUT} | ${VENV_SF}/bin/target-snowflake -c "${SF_CONFIG_FILE}" >> ${PAGERDUTY_STATE} 2>"${STDERRFILE}"')
              catchError(status, "Tap-pagerduty", "Failed to send data.", "${STDERRFILE}")
            }
          }
        } // stage Run Tap-pagerduty

    } // Stages

    post{

      success{
        slackSend(channel: "#analytics-alerts", message: "Tap-pagerduty Worked.", color: "#008000")
      }
      always{
        cleanWs (
          deleteDirs: false,
          patterns: [
            [pattern: 'config*.json', type: 'INCLUDE'],
            [pattern: '*output*.json', type: 'INCLUDE'],
            [pattern: 'stderr*.out', type: 'INCLUDE']
          ]
        )
      } //always
    } // post
} // Pipeline

def setState(state){
  def exists = fileExists state
  if (exists) {
    def file = readFile state
    def last = file.split("\n")[file.split("\n").length-1]
    writeFile file: state, text : last
    def count = sh(returnStdout:true, script:'cat '+ state + ' | tr \' \' \'\n\' | grep bookmark | wc -l').trim()
    echo count
    sh(returnStdout:true, script:'cat ' + state)
  }
  else {
    writeFile file: state, text: '{}'
  }
}

def catchError(status, tap, message, stderrfile){
  if (status != 0) {
    def output = readFile(stderrfile)
    print(output)
    slackSend(channel: "#analytics-alerts", message: "*$tap:* $message \n *Reason:* $output", color: "#ff0000")
    currentBuild.result = 'FAILED'
    error "$message"
  }
}

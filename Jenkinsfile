@Library('shared@0.2')
import gd.mrx.ci.DockerStack

node('builder') {
    stage('Checkout') {
        checkout scm
    }
}

def stack = new gd.mrx.ci.DockerStack(this, 'medfinder-api', [
    steroids_file: 'ci.steroids.yml'
])
stack.execute()

# -*- coding: utf-8 -*-
"""
    Chunky
    ------

    State machine to bulk process large payloads in batches

"""

import boto3
from botocore.exceptions import ClientError

import json
import os
import random
import string
from time import time
from typing import Dict, List

REGION = os.environ.get('REGION', 'us-west-2')
SFN_CLIENT = boto3.client('stepfunctions', region_name=REGION)

#: ARN for patch automation step function
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')


def _start_execution(name: str, input: Dict, state_machine_arn: str):
    """
    Start execution of state machine with given `input`.
        Note - name must be unique for 90 days so epoch timestamp is added for uniqueness
        https://docs.aws.amazon.com/step-functions/latest/dg/limits.html#service-limits-state-machine-executions

    :param name: execution name (NOT step function/state machine name)
    :param input: input data for execution
    :param state_machine_arn: ARN for statemachine to be executed
    :returns: None
    """
    try:
        SFN_CLIENT.start_execution(stateMachineArn=state_machine_arn, name=f'{name}_{time()}', input=json.dumps(input))
    except ClientError:
        raise


def execute_chunker(event: Dict, _c: Dict):
    """
    Lambda function that will start chunking process with payload received.

    :param event: lambda expected event object
    :param _c: lambda expected context object (unused)
    :returns: none
    """
    records = event.get('payload', [])
    _input = {'records': records, 'recordsRemaining': len(records)}
    _start_execution(name='chunky', input=_input, state_machine_arn=STATE_MACHINE_ARN)


def chunk(event: Dict, _c: Dict) -> Dict:
    """
    Lambda function to get the latest active base AMIs to evaluate for patching.

    :param event: lambda expected event object
    :param _c: lambda expected context object (unused)
    :returns: list of current, active AMIs to check for patching
    """
    chunk_size = 5
    records_to_process = event.get('records', [])

    if len(records_to_process) < chunk_size:
        chunk = records_to_process
        records = []
    else:
        chunk = records_to_process[:chunk_size]
        records = records_to_process[chunk_size:]

    # fake processing with random response code
    print(f'This chunk was processed:\n{chunk}')
    response = random.choice([200, 429, 503])

    return {'processedChunk': chunk, 'chunkResponse': response, 'records': records, 'recordsRemaining': len(records)}


def failed_chunk(event: Dict, _c: Dict) -> List[Dict]:
    """
    Lambda function to get the latest active base AMIs to evaluate for patching.

    :param event: lambda expected event object
    :param _c: lambda expected context object (unused)
    :returns: list of current, active AMIs to check for patching
    """
    print(f'These failed to process:\n{event.get("processedChunk")}')
    del event['chunkResponse']
    del event['processedChunk']
    return event

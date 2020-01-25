import logging
import ask_sdk_core.utils as ask_utils
import json
import boto3

from logs import Applogger
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response
from ask_sdk_model.slu.entityresolution import StatusCode

# from ask_sdk_s3.adapter import S3Adapter
# from ask_sdk_s3.object_keygen import user_id_keygen
# from ask_sdk_core.skill_builder import CustomSkillBuilder

# Init Logger
applogger = Applogger(__name__)
logger = applogger.logger

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "テレビのリモコンです"
        reprompt = "テレビをつけたい場合は、テレビをつけて、と言ってください。"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt)
                .response
        )

class RemoteControllIntentHandler(AbstractRequestHandler):
    """Handler for RemoteControll Intent."""

    def __init__(self):

        # Init AWSIoTMQTTClient For Websocket connection
        self.myAWSIoTMQTTClient = None
        self.myAWSIoTMQTTClient = AWSIoTMQTTClient("", useWebsocket=True)
        self.myAWSIoTMQTTClient.configureEndpoint("a1xfsi89ntz6zn-ats.iot.ap-northeast-1.amazonaws.com", 443)
        self.myAWSIoTMQTTClient.configureCredentials("rootCA.pem")

        # AWSIoTMQTTClient connection configuration
        self.myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        self.myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
        self.myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
        self.myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

        # Init device/action list
        self.device_list = {"001":"TV","002":"aircon","003":"light"}
        self.function_list = {"001":"power","002":"volume_up","003":"volume_down"}

        # topic
        self.topic = "$aws/things/RaspberryPi/shadow/update"

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("RemoteControllIntent")(handler_input)

    def handle(self, handler_input):
        # slots
        slots = handler_input.request_envelope.request.intent.slots

        # device_id
        device_id = "001"

        #
        speak_output = "ーーーーー"

        # create a payload
        if slots["btn"].resolutions.resolutions_per_authority[0].status.code == StatusCode.ER_SUCCESS_MATCH:
            btn_id = slots["btn"].resolutions.resolutions_per_authority[0].values[0].value.id
            if btn_id == "001":
                action_id = "001"
                payload = {"state":{"desired":{"{}".format(self.device_list[device_id]):{"{}".format(self.function_list[action_id]):1}}}}
            elif btn_id == "002":
                if slots["action"].resolutions.resolutions_per_authority[0].status.code == StatusCode.ER_SUCCESS_MATCH:
                    action_id = slots["action"].resolutions.resolutions_per_authority[0].values[0].value.id
                    num = slots["num"].value
                    if num != None:
                        payload = {"state":{"desired":{"{}".format(self.device_list[device_id]):{"{}".format(self.function_list[action_id]):int(num)}}}}
                    else:
                        payload = {"state":{"desired":{"{}".format(self.device_list[device_id]):{"{}".format(self.function_list[action_id]):1}}}}

            logger.debug(json.dumps(payload))

            # connct to shadow
            self.myAWSIoTMQTTClient.connect()
            logger.debug('connect to shadow')
            self.myAWSIoTMQTTClient.publish(self.topic, json.dumps(payload), 0)
            logger.debug('update desired')
            self.myAWSIoTMQTTClient.disconnect()
            logger.debug('disconnect to shadow')

            speak_output = "ーーーーー"

        else:
            speak_output = "その操作はできません。テレビをつけたい場合は、テレビをつけて、と言ってください。"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "テレビをつけたい場合は、テレビをつけて、と言ってください。"
        reprompt = "ボリュームを2段階下げたい時には、ボリュームを２つ下げて、と言ってください。"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "またのお越しをお待ちしています"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = intent_name + "というインテントが呼ばれました。"

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "すみません、なんだかうまく行かないようです。もう一度お試しください。"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(RemoteControllIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()

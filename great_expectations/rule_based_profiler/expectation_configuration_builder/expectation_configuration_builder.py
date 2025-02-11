import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Union

from great_expectations.core.batch import Batch, BatchRequest, RuntimeBatchRequest
from great_expectations.core.expectation_configuration import ExpectationConfiguration
from great_expectations.rule_based_profiler.config import ParameterBuilderConfig
from great_expectations.rule_based_profiler.helpers.util import (
    init_rule_parameter_builders,
    set_batch_list_or_batch_request_on_builder,
)
from great_expectations.rule_based_profiler.parameter_builder import ParameterBuilder
from great_expectations.rule_based_profiler.types import (
    Builder,
    Domain,
    ParameterContainer,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ExpectationConfigurationBuilder(Builder, ABC):
    exclude_field_names: Set[str] = Builder.exclude_field_names | {
        "validation_parameter_builders",
    }

    def __init__(
        self,
        expectation_type: str,
        validation_parameter_builder_configs: Optional[
            List[ParameterBuilderConfig]
        ] = None,
        batch_list: Optional[List[Batch]] = None,
        batch_request: Optional[
            Union[str, BatchRequest, RuntimeBatchRequest, dict]
        ] = None,
        data_context: Optional["DataContext"] = None,  # noqa: F821
        **kwargs
    ):
        """
        The ExpectationConfigurationBuilder will build ExpectationConfiguration objects for a Domain from the Rule.

        Args:
            expectation_type: the "expectation_type" argument of "ExpectationConfiguration" object to be emitted.
            validation_parameter_builder_configs: ParameterBuilder configurations, having whose outputs available (as
            fully-qualified parameter names) is pre-requisite for present ExpectationConfigurationBuilder instance.
            batch_list: explicitly passed Batch objects for parameter computation (take precedence over batch_request).
            batch_request: specified in ParameterBuilder configuration to get Batch objects for parameter computation.
            data_context: DataContext
            kwargs: additional arguments
        """

        super().__init__(
            batch_list=batch_list,
            batch_request=batch_request,
            data_context=data_context,
        )

        self._expectation_type = expectation_type

        self._validation_parameter_builders = init_rule_parameter_builders(
            parameter_builder_configs=validation_parameter_builder_configs,
            data_context=self._data_context,
        )

        """
        Since ExpectationConfigurationBuilderConfigSchema allows arbitrary fields (as ExpectationConfiguration kwargs)
        to be provided, they must be all converted to public property accessors and/or public fields in order for all
        provisions by Builder, SerializableDictDot, and DictDot to operate properly in compliance with their interfaces.
        """
        for k, v in kwargs.items():
            setattr(self, k, v)
            logger.debug(
                'Setting unknown kwarg (%s, %s) provided to constructor as argument in "%s".',
                k,
                v,
                self.__class__.__name__,
            )

    def build_expectation_configuration(
        self,
        parameter_container: ParameterContainer,
        domain: Domain,
        variables: Optional[ParameterContainer] = None,
        parameters: Optional[Dict[str, ParameterContainer]] = None,
    ) -> ExpectationConfiguration:
        self._resolve_validation_dependencies(
            parameter_container=parameter_container,
            domain=domain,
            variables=variables,
            parameters=parameters,
        )

        return self._build_expectation_configuration(
            domain=domain, variables=variables, parameters=parameters
        )

    def _resolve_validation_dependencies(
        self,
        parameter_container: ParameterContainer,
        domain: Domain,
        variables: Optional[ParameterContainer] = None,
        parameters: Optional[Dict[str, ParameterContainer]] = None,
    ) -> None:
        validation_parameter_builders: List[ParameterBuilder] = (
            self.validation_parameter_builders or []
        )

        validation_parameter_builder: ParameterBuilder
        for validation_parameter_builder in validation_parameter_builders:
            set_batch_list_or_batch_request_on_builder(
                builder=validation_parameter_builder,
                batch_list=self.batch_list,
                batch_request=self.batch_request,
                force_batch_data=False,
            )
            validation_parameter_builder.build_parameters(
                parameter_container=parameter_container,
                domain=domain,
                variables=variables,
                parameters=parameters,
            )

    @abstractmethod
    def _build_expectation_configuration(
        self,
        domain: Domain,
        variables: Optional[ParameterContainer] = None,
        parameters: Optional[Dict[str, ParameterContainer]] = None,
    ) -> ExpectationConfiguration:
        pass

    @property
    def expectation_type(self) -> str:
        return self._expectation_type

    @property
    def validation_parameter_builders(self) -> Optional[List[ParameterBuilder]]:
        return self._validation_parameter_builders

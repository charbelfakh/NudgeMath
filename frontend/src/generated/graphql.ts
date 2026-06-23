/* eslint-disable */
/** Internal type. DO NOT USE DIRECTLY. */
type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
/** Internal type. DO NOT USE DIRECTLY. */
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
import type { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';
export type HintRequestInput = {
  correctAnswer?: string | null | undefined;
  gradeLevel?: string | null | undefined;
  problem: string;
  studentAnswer: string;
  subject?: string | null | undefined;
};

export type GenerateHintMutationVariables = Exact<{
  request: HintRequestInput;
}>;


export type GenerateHintMutation = { generateHint: { hintText: string, revealsAnswer: boolean, answerCorrect: boolean, meta: { model: string | null, provider: string | null, latencyMs: number | null, error: string | null } } };

export type HintsQueryVariables = Exact<{ [key: string]: never; }>;


export type HintsQuery = { hints: Array<{ caseId: string | null, problem: string, studentAnswer: string, correctAnswer: string }> };

export type EvaluateCaseMutationVariables = Exact<{
  caseId: string;
  withJudge: boolean;
}>;


export type EvaluateCaseMutation = { evaluateCase: { passed: boolean, caseId: string | null, problem: string, hintText: string, revealsAnswer: boolean, summary: string, flagDisagreement: boolean, modelAnswerDisagreement: boolean | null, meta: { model: string | null, provider: string | null, latencyMs: number | null, error: string | null }, deterministic: { passed: boolean, checks: Array<{ name: string, passed: boolean, detail: string }> }, judge: { passed: boolean, score: number, checks: Array<{ name: string, passed: boolean, detail: string }>, meta: { model: string | null, latencyMs: number | null, error: string | null } } | null } };


export const GenerateHintDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"GenerateHint"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"request"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"HintRequestInput"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"generateHint"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"request"},"value":{"kind":"Variable","name":{"kind":"Name","value":"request"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"hintText"}},{"kind":"Field","name":{"kind":"Name","value":"revealsAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"answerCorrect"}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"latencyMs"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]}}]} as unknown as DocumentNode<GenerateHintMutation, GenerateHintMutationVariables>;
export const HintsDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"Hints"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"hints"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"caseId"}},{"kind":"Field","name":{"kind":"Name","value":"problem"}},{"kind":"Field","name":{"kind":"Name","value":"studentAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"correctAnswer"}}]}}]}}]} as unknown as DocumentNode<HintsQuery, HintsQueryVariables>;
export const EvaluateCaseDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"EvaluateCase"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"caseId"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"withJudge"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"Boolean"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"evaluateCase"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"caseId"},"value":{"kind":"Variable","name":{"kind":"Name","value":"caseId"}}},{"kind":"Argument","name":{"kind":"Name","value":"withJudge"},"value":{"kind":"Variable","name":{"kind":"Name","value":"withJudge"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"caseId"}},{"kind":"Field","name":{"kind":"Name","value":"problem"}},{"kind":"Field","name":{"kind":"Name","value":"hintText"}},{"kind":"Field","name":{"kind":"Name","value":"revealsAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"summary"}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"latencyMs"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}},{"kind":"Field","name":{"kind":"Name","value":"flagDisagreement"}},{"kind":"Field","name":{"kind":"Name","value":"modelAnswerDisagreement"}},{"kind":"Field","name":{"kind":"Name","value":"deterministic"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"checks"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"name"}},{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"detail"}}]}}]}},{"kind":"Field","name":{"kind":"Name","value":"judge"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"score"}},{"kind":"Field","name":{"kind":"Name","value":"checks"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"name"}},{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"detail"}}]}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"latencyMs"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]}}]}}]} as unknown as DocumentNode<EvaluateCaseMutation, EvaluateCaseMutationVariables>;
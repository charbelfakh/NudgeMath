/* eslint-disable */
/** Internal type. DO NOT USE DIRECTLY. */
type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
/** Internal type. DO NOT USE DIRECTLY. */
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
import type { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';
export type ConversationTurnInput = {
  role: string;
  text: string;
};

export type HintRequestInput = {
  correctAnswer?: string | null | undefined;
  gradeLevel?: string | null | undefined;
  history?: Array<ConversationTurnInput> | null | undefined;
  problem: string;
  problemId?: string | null | undefined;
  studentAnswer: string;
  subject?: string | null | undefined;
};

export type GenerateHintMutationVariables = Exact<{
  request: HintRequestInput;
}>;


export type GenerateHintMutation = { generateHint: { hintText: string, revealsAnswer: boolean, answerCorrect: boolean, meta: { model: string | null, provider: string | null, latencyMs: number | null, error: string | null } } };

export type TranscribeProblemMutationVariables = Exact<{
  image: string;
}>;


export type TranscribeProblemMutation = { transcribeProblem: { problem: string, studentAnswer: string, meta: { model: string | null, provider: string | null, latencyMs: number | null, error: string | null } } };

export type GenerateProblemMutationVariables = Exact<{
  gradeLevel: string;
  topic?: string | null | undefined;
  difficulty?: string | null | undefined;
  mode?: string | null | undefined;
}>;


export type GenerateProblemMutation = { generateProblem: { problem: string, problemId: string, gradeLevel: string, topic: string, difficulty: string, source: string, verified: boolean, meta: { model: string | null, provider: string | null, error: string | null } } };

export type HintsQueryVariables = Exact<{ [key: string]: never; }>;


export type HintsQuery = { hints: Array<{ caseId: string | null, problem: string, studentAnswer: string, correctAnswer: string }> };

export type CurriculumQueryVariables = Exact<{
  gradeLevel?: string | null | undefined;
}>;


export type CurriculumQuery = { curriculum: Array<{ topic: string, template: boolean, difficulties: Array<string>, description: string }> };

export type LoginMutationVariables = Exact<{
  username: string;
  password: string;
}>;


export type LoginMutation = { login: { token: string | null, username: string | null, expiresAt: number | null, error: string | null } };

export type AdminModelsQueryVariables = Exact<{ [key: string]: never; }>;


export type AdminModelsQuery = { adminModels: { visionModel: string, generationModel: string, solverModel: string, visionPresets: Array<{ name: string, provider: string, model: string }>, generationPresets: Array<{ name: string, provider: string, model: string }>, solverPresets: Array<{ name: string, provider: string, model: string }> } | null };

export type SetModelMutationVariables = Exact<{
  kind: string;
  preset: string;
}>;


export type SetModelMutation = { setModel: { visionModel: string, generationModel: string, solverModel: string } | null };

export type SolveProblemMutationVariables = Exact<{
  problem: string;
  gradeLevel?: string | null | undefined;
}>;


export type SolveProblemMutation = { solveProblem: { solutionText: string, finalAnswer: string, meta: { model: string | null, provider: string | null, latencyMs: number | null, error: string | null } } | null };

export type ClaudeSubscriptionQueryVariables = Exact<{ [key: string]: never; }>;


export type ClaudeSubscriptionQuery = { claudeSubscription: { signedIn: boolean, detail: string, model: string, effort: string | null } | null };

export type SetClaudeEffortMutationVariables = Exact<{
  effort?: string | null | undefined;
}>;


export type SetClaudeEffortMutation = { setClaudeEffort: { signedIn: boolean, effort: string | null } | null };

export type StartClaudeLoginMutationVariables = Exact<{ [key: string]: never; }>;


export type StartClaudeLoginMutation = { startClaudeLogin: { signedIn: boolean, url: string | null } | null };

export type FinishClaudeLoginMutationVariables = Exact<{
  code: string;
}>;


export type FinishClaudeLoginMutation = { finishClaudeLogin: { signedIn: boolean, detail: string, error: string | null } | null };

export type DisconnectClaudeSubscriptionMutationVariables = Exact<{ [key: string]: never; }>;


export type DisconnectClaudeSubscriptionMutation = { disconnectClaudeSubscription: { signedIn: boolean, detail: string, model: string } | null };

export type RevealAnswerQueryVariables = Exact<{
  problemId: string;
}>;


export type RevealAnswerQuery = { revealAnswer: { problemId: string, correctAnswer: string | null, found: boolean } | null };

export type EvaluateCaseMutationVariables = Exact<{
  caseId: string;
  withJudge: boolean;
}>;


export type EvaluateCaseMutation = { evaluateCase: { passed: boolean, caseId: string | null, problem: string, hintText: string, revealsAnswer: boolean, summary: string, flagDisagreement: boolean, modelAnswerDisagreement: boolean | null, meta: { model: string | null, provider: string | null, latencyMs: number | null, error: string | null }, deterministic: { passed: boolean, checks: Array<{ name: string, passed: boolean, detail: string }> }, judge: { passed: boolean, score: number, checks: Array<{ name: string, passed: boolean, detail: string }>, meta: { model: string | null, latencyMs: number | null, error: string | null } } | null } | null };


export const GenerateHintDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"GenerateHint"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"request"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"HintRequestInput"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"generateHint"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"request"},"value":{"kind":"Variable","name":{"kind":"Name","value":"request"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"hintText"}},{"kind":"Field","name":{"kind":"Name","value":"revealsAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"answerCorrect"}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"latencyMs"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]}}]} as unknown as DocumentNode<GenerateHintMutation, GenerateHintMutationVariables>;
export const TranscribeProblemDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"TranscribeProblem"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"image"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"transcribeProblem"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"image"},"value":{"kind":"Variable","name":{"kind":"Name","value":"image"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"problem"}},{"kind":"Field","name":{"kind":"Name","value":"studentAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"latencyMs"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]}}]} as unknown as DocumentNode<TranscribeProblemMutation, TranscribeProblemMutationVariables>;
export const GenerateProblemDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"GenerateProblem"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"gradeLevel"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"topic"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"difficulty"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"mode"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"generateProblem"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"gradeLevel"},"value":{"kind":"Variable","name":{"kind":"Name","value":"gradeLevel"}}},{"kind":"Argument","name":{"kind":"Name","value":"topic"},"value":{"kind":"Variable","name":{"kind":"Name","value":"topic"}}},{"kind":"Argument","name":{"kind":"Name","value":"difficulty"},"value":{"kind":"Variable","name":{"kind":"Name","value":"difficulty"}}},{"kind":"Argument","name":{"kind":"Name","value":"mode"},"value":{"kind":"Variable","name":{"kind":"Name","value":"mode"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"problem"}},{"kind":"Field","name":{"kind":"Name","value":"problemId"}},{"kind":"Field","name":{"kind":"Name","value":"gradeLevel"}},{"kind":"Field","name":{"kind":"Name","value":"topic"}},{"kind":"Field","name":{"kind":"Name","value":"difficulty"}},{"kind":"Field","name":{"kind":"Name","value":"source"}},{"kind":"Field","name":{"kind":"Name","value":"verified"}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]}}]} as unknown as DocumentNode<GenerateProblemMutation, GenerateProblemMutationVariables>;
export const HintsDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"Hints"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"hints"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"caseId"}},{"kind":"Field","name":{"kind":"Name","value":"problem"}},{"kind":"Field","name":{"kind":"Name","value":"studentAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"correctAnswer"}}]}}]}}]} as unknown as DocumentNode<HintsQuery, HintsQueryVariables>;
export const CurriculumDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"Curriculum"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"gradeLevel"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"curriculum"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"gradeLevel"},"value":{"kind":"Variable","name":{"kind":"Name","value":"gradeLevel"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"topic"}},{"kind":"Field","name":{"kind":"Name","value":"template"}},{"kind":"Field","name":{"kind":"Name","value":"difficulties"}},{"kind":"Field","name":{"kind":"Name","value":"description"}}]}}]}}]} as unknown as DocumentNode<CurriculumQuery, CurriculumQueryVariables>;
export const LoginDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"Login"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"username"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"password"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"login"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"username"},"value":{"kind":"Variable","name":{"kind":"Name","value":"username"}}},{"kind":"Argument","name":{"kind":"Name","value":"password"},"value":{"kind":"Variable","name":{"kind":"Name","value":"password"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"token"}},{"kind":"Field","name":{"kind":"Name","value":"username"}},{"kind":"Field","name":{"kind":"Name","value":"expiresAt"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]} as unknown as DocumentNode<LoginMutation, LoginMutationVariables>;
export const AdminModelsDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"AdminModels"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"adminModels"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"visionModel"}},{"kind":"Field","name":{"kind":"Name","value":"generationModel"}},{"kind":"Field","name":{"kind":"Name","value":"solverModel"}},{"kind":"Field","name":{"kind":"Name","value":"visionPresets"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"name"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"model"}}]}},{"kind":"Field","name":{"kind":"Name","value":"generationPresets"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"name"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"model"}}]}},{"kind":"Field","name":{"kind":"Name","value":"solverPresets"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"name"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"model"}}]}}]}}]}}]} as unknown as DocumentNode<AdminModelsQuery, AdminModelsQueryVariables>;
export const SetModelDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"SetModel"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"kind"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"preset"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"setModel"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"kind"},"value":{"kind":"Variable","name":{"kind":"Name","value":"kind"}}},{"kind":"Argument","name":{"kind":"Name","value":"preset"},"value":{"kind":"Variable","name":{"kind":"Name","value":"preset"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"visionModel"}},{"kind":"Field","name":{"kind":"Name","value":"generationModel"}},{"kind":"Field","name":{"kind":"Name","value":"solverModel"}}]}}]}}]} as unknown as DocumentNode<SetModelMutation, SetModelMutationVariables>;
export const SolveProblemDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"SolveProblem"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"problem"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"gradeLevel"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"solveProblem"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"problem"},"value":{"kind":"Variable","name":{"kind":"Name","value":"problem"}}},{"kind":"Argument","name":{"kind":"Name","value":"gradeLevel"},"value":{"kind":"Variable","name":{"kind":"Name","value":"gradeLevel"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"solutionText"}},{"kind":"Field","name":{"kind":"Name","value":"finalAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"latencyMs"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]}}]} as unknown as DocumentNode<SolveProblemMutation, SolveProblemMutationVariables>;
export const ClaudeSubscriptionDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"ClaudeSubscription"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"claudeSubscription"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"signedIn"}},{"kind":"Field","name":{"kind":"Name","value":"detail"}},{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"effort"}}]}}]}}]} as unknown as DocumentNode<ClaudeSubscriptionQuery, ClaudeSubscriptionQueryVariables>;
export const SetClaudeEffortDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"SetClaudeEffort"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"effort"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"setClaudeEffort"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"effort"},"value":{"kind":"Variable","name":{"kind":"Name","value":"effort"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"signedIn"}},{"kind":"Field","name":{"kind":"Name","value":"effort"}}]}}]}}]} as unknown as DocumentNode<SetClaudeEffortMutation, SetClaudeEffortMutationVariables>;
export const StartClaudeLoginDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"StartClaudeLogin"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"startClaudeLogin"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"signedIn"}},{"kind":"Field","name":{"kind":"Name","value":"url"}}]}}]}}]} as unknown as DocumentNode<StartClaudeLoginMutation, StartClaudeLoginMutationVariables>;
export const FinishClaudeLoginDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"FinishClaudeLogin"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"code"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"finishClaudeLogin"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"code"},"value":{"kind":"Variable","name":{"kind":"Name","value":"code"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"signedIn"}},{"kind":"Field","name":{"kind":"Name","value":"detail"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]} as unknown as DocumentNode<FinishClaudeLoginMutation, FinishClaudeLoginMutationVariables>;
export const DisconnectClaudeSubscriptionDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"DisconnectClaudeSubscription"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"disconnectClaudeSubscription"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"signedIn"}},{"kind":"Field","name":{"kind":"Name","value":"detail"}},{"kind":"Field","name":{"kind":"Name","value":"model"}}]}}]}}]} as unknown as DocumentNode<DisconnectClaudeSubscriptionMutation, DisconnectClaudeSubscriptionMutationVariables>;
export const RevealAnswerDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"RevealAnswer"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"problemId"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"revealAnswer"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"problemId"},"value":{"kind":"Variable","name":{"kind":"Name","value":"problemId"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"problemId"}},{"kind":"Field","name":{"kind":"Name","value":"correctAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"found"}}]}}]}}]} as unknown as DocumentNode<RevealAnswerQuery, RevealAnswerQueryVariables>;
export const EvaluateCaseDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"EvaluateCase"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"caseId"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"withJudge"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"Boolean"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"evaluateCase"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"caseId"},"value":{"kind":"Variable","name":{"kind":"Name","value":"caseId"}}},{"kind":"Argument","name":{"kind":"Name","value":"withJudge"},"value":{"kind":"Variable","name":{"kind":"Name","value":"withJudge"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"caseId"}},{"kind":"Field","name":{"kind":"Name","value":"problem"}},{"kind":"Field","name":{"kind":"Name","value":"hintText"}},{"kind":"Field","name":{"kind":"Name","value":"revealsAnswer"}},{"kind":"Field","name":{"kind":"Name","value":"summary"}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"provider"}},{"kind":"Field","name":{"kind":"Name","value":"latencyMs"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}},{"kind":"Field","name":{"kind":"Name","value":"flagDisagreement"}},{"kind":"Field","name":{"kind":"Name","value":"modelAnswerDisagreement"}},{"kind":"Field","name":{"kind":"Name","value":"deterministic"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"checks"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"name"}},{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"detail"}}]}}]}},{"kind":"Field","name":{"kind":"Name","value":"judge"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"score"}},{"kind":"Field","name":{"kind":"Name","value":"checks"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"name"}},{"kind":"Field","name":{"kind":"Name","value":"passed"}},{"kind":"Field","name":{"kind":"Name","value":"detail"}}]}},{"kind":"Field","name":{"kind":"Name","value":"meta"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"model"}},{"kind":"Field","name":{"kind":"Name","value":"latencyMs"}},{"kind":"Field","name":{"kind":"Name","value":"error"}}]}}]}}]}}]}}]} as unknown as DocumentNode<EvaluateCaseMutation, EvaluateCaseMutationVariables>;
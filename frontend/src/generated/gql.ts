/* eslint-disable */
import * as types from './graphql';
import type { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';

/**
 * Map of all GraphQL operations in the project.
 *
 * This map has several performance disadvantages:
 * 1. It is not tree-shakeable, so it will include all operations in the project.
 * 2. It is not minifiable, so the string of a GraphQL query will be multiple times inside the bundle.
 * 3. It does not support dead code elimination, so it will add unused operations.
 *
 * Therefore it is highly recommended to use the babel or swc plugin for production.
 * Learn more about it here: https://the-guild.dev/graphql/codegen/plugins/presets/preset-client#reducing-bundle-size
 */
type Documents = {
    "mutation GenerateHint($request: HintRequestInput!) {\n  generateHint(request: $request) {\n    hintText\n    revealsAnswer\n    answerCorrect\n    meta {\n      model\n      provider\n      latencyMs\n      error\n    }\n  }\n}\n\nquery Hints {\n  hints {\n    caseId\n    problem\n    studentAnswer\n    correctAnswer\n  }\n}\n\nmutation EvaluateCase($caseId: String!, $withJudge: Boolean!) {\n  evaluateCase(caseId: $caseId, withJudge: $withJudge) {\n    passed\n    caseId\n    problem\n    hintText\n    revealsAnswer\n    summary\n    meta {\n      model\n      provider\n      latencyMs\n      error\n    }\n    flagDisagreement\n    modelAnswerDisagreement\n    deterministic {\n      passed\n      checks {\n        name\n        passed\n        detail\n      }\n    }\n    judge {\n      passed\n      score\n      checks {\n        name\n        passed\n        detail\n      }\n      meta {\n        model\n        latencyMs\n        error\n      }\n    }\n  }\n}": typeof types.GenerateHintDocument,
};
const documents: Documents = {
    "mutation GenerateHint($request: HintRequestInput!) {\n  generateHint(request: $request) {\n    hintText\n    revealsAnswer\n    answerCorrect\n    meta {\n      model\n      provider\n      latencyMs\n      error\n    }\n  }\n}\n\nquery Hints {\n  hints {\n    caseId\n    problem\n    studentAnswer\n    correctAnswer\n  }\n}\n\nmutation EvaluateCase($caseId: String!, $withJudge: Boolean!) {\n  evaluateCase(caseId: $caseId, withJudge: $withJudge) {\n    passed\n    caseId\n    problem\n    hintText\n    revealsAnswer\n    summary\n    meta {\n      model\n      provider\n      latencyMs\n      error\n    }\n    flagDisagreement\n    modelAnswerDisagreement\n    deterministic {\n      passed\n      checks {\n        name\n        passed\n        detail\n      }\n    }\n    judge {\n      passed\n      score\n      checks {\n        name\n        passed\n        detail\n      }\n      meta {\n        model\n        latencyMs\n        error\n      }\n    }\n  }\n}": types.GenerateHintDocument,
};

/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 *
 *
 * @example
 * ```ts
 * const query = graphql(`query GetUser($id: ID!) { user(id: $id) { name } }`);
 * ```
 *
 * The query argument is unknown!
 * Please regenerate the types.
 */
export function graphql(source: string): unknown;

/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(source: "mutation GenerateHint($request: HintRequestInput!) {\n  generateHint(request: $request) {\n    hintText\n    revealsAnswer\n    answerCorrect\n    meta {\n      model\n      provider\n      latencyMs\n      error\n    }\n  }\n}\n\nquery Hints {\n  hints {\n    caseId\n    problem\n    studentAnswer\n    correctAnswer\n  }\n}\n\nmutation EvaluateCase($caseId: String!, $withJudge: Boolean!) {\n  evaluateCase(caseId: $caseId, withJudge: $withJudge) {\n    passed\n    caseId\n    problem\n    hintText\n    revealsAnswer\n    summary\n    meta {\n      model\n      provider\n      latencyMs\n      error\n    }\n    flagDisagreement\n    modelAnswerDisagreement\n    deterministic {\n      passed\n      checks {\n        name\n        passed\n        detail\n      }\n    }\n    judge {\n      passed\n      score\n      checks {\n        name\n        passed\n        detail\n      }\n      meta {\n        model\n        latencyMs\n        error\n      }\n    }\n  }\n}"): (typeof documents)["mutation GenerateHint($request: HintRequestInput!) {\n  generateHint(request: $request) {\n    hintText\n    revealsAnswer\n    answerCorrect\n    meta {\n      model\n      provider\n      latencyMs\n      error\n    }\n  }\n}\n\nquery Hints {\n  hints {\n    caseId\n    problem\n    studentAnswer\n    correctAnswer\n  }\n}\n\nmutation EvaluateCase($caseId: String!, $withJudge: Boolean!) {\n  evaluateCase(caseId: $caseId, withJudge: $withJudge) {\n    passed\n    caseId\n    problem\n    hintText\n    revealsAnswer\n    summary\n    meta {\n      model\n      provider\n      latencyMs\n      error\n    }\n    flagDisagreement\n    modelAnswerDisagreement\n    deterministic {\n      passed\n      checks {\n        name\n        passed\n        detail\n      }\n    }\n    judge {\n      passed\n      score\n      checks {\n        name\n        passed\n        detail\n      }\n      meta {\n        model\n        latencyMs\n        error\n      }\n    }\n  }\n}"];

export function graphql(source: string) {
  return (documents as any)[source] ?? {};
}

export type DocumentType<TDocumentNode extends DocumentNode<any, any>> = TDocumentNode extends DocumentNode<  infer TType,  any>  ? TType  : never;
// Fictional examples only. No measured Deep Sigma performance.
window.LiddellExamples = [
  {
    "label": "Preparation pays off",
    "data": {
      "schema_version": "1.0",
      "data_kind": "illustrative",
      "title": "Illustration — preparation pays off",
      "cases": [
        {
          "case_id": "POLICY-001",
          "baseline": {
            "elapsed_minutes": 200,
            "effort_minutes": {
              "preparation": 10,
              "execution": 40,
              "review": 10,
              "clarification": 30,
              "rework": 50
            },
            "clarification_cycles": 4,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          },
          "cerpa": {
            "elapsed_minutes": 120,
            "effort_minutes": {
              "preparation": 25,
              "execution": 40,
              "review": 20,
              "clarification": 5,
              "rework": 10
            },
            "clarification_cycles": 1,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          }
        },
        {
          "case_id": "POLICY-002",
          "baseline": {
            "elapsed_minutes": 300,
            "effort_minutes": {
              "preparation": 10,
              "execution": 50,
              "review": 15,
              "clarification": 45,
              "rework": 80
            },
            "clarification_cycles": 6,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          },
          "cerpa": {
            "elapsed_minutes": 180,
            "effort_minutes": {
              "preparation": 30,
              "execution": 50,
              "review": 30,
              "clarification": 10,
              "rework": 20
            },
            "clarification_cycles": 2,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          }
        }
      ]
    }
  },
  {
    "label": "Overhead exceeds benefit",
    "data": {
      "schema_version": "1.0",
      "data_kind": "illustrative",
      "title": "Illustration — overhead exceeds benefit",
      "cases": [
        {
          "case_id": "ROUTINE-001",
          "baseline": {
            "elapsed_minutes": 60,
            "effort_minutes": {
              "preparation": 5,
              "execution": 30,
              "review": 5,
              "clarification": 5,
              "rework": 5
            },
            "clarification_cycles": 1,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          },
          "cerpa": {
            "elapsed_minutes": 75,
            "effort_minutes": {
              "preparation": 20,
              "execution": 30,
              "review": 15,
              "clarification": 2,
              "rework": 3
            },
            "clarification_cycles": 1,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          }
        }
      ]
    }
  },
  {
    "label": "Completion gaps",
    "data": {
      "schema_version": "1.0",
      "data_kind": "illustrative",
      "title": "Illustration — completion gaps remain visible",
      "cases": [
        {
          "case_id": "POLICY-001",
          "baseline": {
            "elapsed_minutes": 200,
            "effort_minutes": {
              "preparation": 10,
              "execution": 40,
              "review": 10,
              "clarification": 30,
              "rework": 50
            },
            "clarification_cycles": 4,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          },
          "cerpa": {
            "elapsed_minutes": 120,
            "effort_minutes": {
              "preparation": 25,
              "execution": 40,
              "review": 20,
              "clarification": 5,
              "rework": 10
            },
            "clarification_cycles": 1,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          }
        },
        {
          "case_id": "POLICY-003",
          "baseline": {
            "elapsed_minutes": 240,
            "effort_minutes": {
              "preparation": 10,
              "execution": 40,
              "review": 20,
              "clarification": 35,
              "rework": 45
            },
            "clarification_cycles": 5,
            "unresolved_contradictions": 2,
            "closed": false,
            "supported": false,
            "authorized": false
          },
          "cerpa": {
            "elapsed_minutes": 180,
            "effort_minutes": {
              "preparation": 25,
              "execution": 40,
              "review": 25,
              "clarification": 10,
              "rework": 15
            },
            "clarification_cycles": 2,
            "unresolved_contradictions": 0,
            "closed": true,
            "supported": true,
            "authorized": true
          }
        },
        {
          "case_id": "POLICY-004",
          "baseline": {
            "elapsed_minutes": 240,
            "effort_minutes": {
              "preparation": 5,
              "execution": 30,
              "review": 10,
              "clarification": 25,
              "rework": 40
            },
            "clarification_cycles": 4,
            "unresolved_contradictions": 3,
            "closed": false,
            "supported": false,
            "authorized": false
          },
          "cerpa": {
            "elapsed_minutes": 240,
            "effort_minutes": {
              "preparation": 20,
              "execution": 30,
              "review": 30,
              "clarification": 15,
              "rework": 20
            },
            "clarification_cycles": 2,
            "unresolved_contradictions": 1,
            "closed": false,
            "supported": false,
            "authorized": false
          }
        }
      ]
    }
  }
];

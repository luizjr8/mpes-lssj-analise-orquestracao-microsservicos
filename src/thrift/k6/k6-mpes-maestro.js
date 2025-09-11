import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-vus',
      vus: 1000,
      duration: '5m',
      exec: 'default',
    },
  },
}

// Load the file once in the init context. Path is relative to this script's directory.
const fileData = open('./input/cenario1.mp3', 'b');

export default function () {
  const formData = {
    file: http.file(fileData, 'cenario1.mp3', 'audio/mpeg'),
  };

  const res = http.post('http://localhost:7000/assist', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  console.log(res.body);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response contains text': (r) => r.body && r.body.includes('text'),
  });
}
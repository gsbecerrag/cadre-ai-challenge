import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { App } from './App'

describe('the app root', () => {
  it('renders the mock cadreai.com host page at the root route', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'From AI Confusion to AI Confidence.' }),
    ).toBeInTheDocument()
  })
})

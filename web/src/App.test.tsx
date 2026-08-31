import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { App } from './App'

describe('the placeholder chat page', () => {
  it('shows the Cadre wordmark', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Cadre AI' })).toBeInTheDocument()
  })

  it('offers a composer that is disabled until the Assistant ships', () => {
    render(<App />)

    const composer = screen.getByRole('textbox', { name: /message the assistant/i })
    expect(composer).toBeDisabled()
    expect(composer).toHaveAttribute('placeholder', 'coming soon')
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
  })
})

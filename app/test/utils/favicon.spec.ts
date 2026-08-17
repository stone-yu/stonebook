import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mdiBookshelf } from '@mdi/js'
import { describe, expect, it } from 'vitest'

describe('site favicon', () => {
    it('uses the same bookshelf shape as the shelf menu', () => {
        const svg = readFileSync(resolve('public/logo/bookshelf.svg'), 'utf8')
        const config = readFileSync(resolve('nuxt.config.ts'), 'utf8')

        expect(svg).toContain(`d="${mdiBookshelf}"`)
        expect(config).toContain("href: '/logo/bookshelf.svg'")
        expect(config).toContain("type: 'image/svg+xml'")
    })
})

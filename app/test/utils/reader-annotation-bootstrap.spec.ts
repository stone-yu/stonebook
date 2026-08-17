import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('reader annotation bootstrap', () => {
    it('retries until the asynchronous EPUB rendition is ready', () => {
        const reader = readFileSync(resolve('../webserver/resources/book/creader.html'), 'utf8')

        expect(reader).toContain('if (!instance || !instance.rendition)')
        expect(reader).toContain('annotationSetupTimer = window.setTimeout')
        expect(reader).toContain('window.clearTimeout(annotationSetupTimer)')
        expect(reader).toContain('setupAnnotationRendition()')
        expect(reader).toContain("instance.rendition.on('rendered'")
        expect(reader).toContain("instance.rendition.on('markClicked'")
    })
})

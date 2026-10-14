import { fireEvent, render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { useUrlState } from './url-state';
function Filters() {
  const [params, update] = useUrlState();
  return (
    <>
      <button
        onClick={() => {
          update((next) => next.delete('q'));
          update((next) => next.set('member', 'member-two'));
        }}
      >
        清空并筛选
      </button>
      <output>{params.toString()}</output>
    </>
  );
}
describe('URL filter state', () => {
  it('composes rapid edits without restoring a cleared search and preserves organization scope', () => {
    window.history.replaceState(null, '', '/tasks?organization=org-1&q=old-search');
    render(
      <BrowserRouter>
        <Filters />
      </BrowserRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: '清空并筛选' }));
    expect(new URLSearchParams(window.location.search).get('q')).toBeNull();
    expect(new URLSearchParams(window.location.search).get('member')).toBe('member-two');
    expect(new URLSearchParams(window.location.search).get('organization')).toBe('org-1');
    expect(screen.getByRole('status')).toHaveTextContent('member=member-two');
  });
});

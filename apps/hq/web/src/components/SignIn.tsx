import { BotAvatar } from '../avatar/BotAvatar';

/** This install belongs to one person on one machine: signing in is a one-time link made on that machine. */
export function SignIn() {
  return (
    <div className="signin">
      <div className="signin__card">
        <div className="signin__hero">
          <BotAvatar shape="blob" color="cyan" size={84} />
        </div>
        <h1 className="signin__title">Jarvis HQ</h1>
        <p className="signin__sub">Your team of AI agents, each with its own browser and workspace, on this machine.</p>
        <p className="signin__foot">This browser is not signed in. In the project folder run <code>npm run open</code> and it opens here, signed in.</p>
      </div>
    </div>
  );
}

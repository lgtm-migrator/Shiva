using UnityEngine;
using MLAgents;
using System.Collections;

public class Ball3DAcademy : Academy
{
    public override void AcademyReset()
    {
        Physics.gravity = new Vector3(0, -resetParameters["gravity"], 0);
    }

    public override void AcademyStep()
    {
	
    }
}

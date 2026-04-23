import { useEffect, useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  buildNewInstanceFormValues,
  formValuesToInstance,
  instanceToFormValues,
  type InstanceFormValues,
} from "@/forms/instanceForm";
import type { Instance, Profile } from "@/lib/types/admin";

type InstancesPageProps = {
  instances: Instance[];
  profiles: Profile[];
  busy: boolean;
  onSaveInstance: (instanceId: string, instance: Instance) => Promise<void>;
  onCreateInstance: (instance: Instance) => Promise<void>;
  onDeleteInstance: (instanceId: string) => Promise<void>;
};

function FieldError({ message }: { message?: string }) {
  if (!message) {
    return null;
  }

  return <p className="text-sm text-destructive">{message}</p>;
}

export function InstancesPage({
  instances,
  profiles,
  busy,
  onSaveInstance,
  onCreateInstance,
  onDeleteInstance,
}: InstancesPageProps) {
  const [selectedId, setSelectedId] = useState<string | null>(instances[0]?.id ?? null);
  const [isCreating, setIsCreating] = useState(false);

  const {
    control,
    formState: { errors, isDirty },
    handleSubmit,
    register,
    reset,
    watch,
  } = useForm<InstanceFormValues>({
    defaultValues:
      instances[0] != null
        ? instanceToFormValues(instances[0])
        : buildNewInstanceFormValues(instances, profiles),
  });

  useEffect(() => {
    if (isCreating) {
      return;
    }

    if (selectedId == null) {
      const next = instances[0] ?? null;
      setSelectedId(next?.id ?? null);
      reset(next ? instanceToFormValues(next) : buildNewInstanceFormValues(instances, profiles));
      return;
    }

    const next = instances.find((instance) => instance.id === selectedId) ?? instances[0] ?? null;
    if (next?.id !== selectedId) {
      setSelectedId(next?.id ?? null);
      reset(next ? instanceToFormValues(next) : buildNewInstanceFormValues(instances, profiles));
      return;
    }

    if (!isDirty && next != null) {
      reset(instanceToFormValues(next));
    }
  }, [instances, isCreating, profiles, reset, selectedId, isDirty]);

  const currentLabel = watch("label");
  const activeInstance = useMemo(
    () => instances.find((instance) => instance.id === selectedId) ?? instances[0] ?? null,
    [instances, selectedId],
  );

  if (!isCreating && activeInstance == null) {
    return (
      <section className="panel-card">
        <h2>Instances</h2>
        <p className="muted">No draft instances are loaded yet.</p>
      </section>
    );
  }

  async function onSubmit(values: InstanceFormValues) {
    const instance = formValuesToInstance(values);

    if (isCreating) {
      await onCreateInstance(instance);
      setIsCreating(false);
      setSelectedId(instance.id);
      return;
    }

    await onSaveInstance(instance.id, instance);
  }

  return (
    <section className="editor-layout">
      <aside className="sidebar-card">
        <div className="sidebar-header">
          <div>
            <p className="eyebrow">Draft Instances</p>
            <h2>Instances</h2>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setIsCreating(true);
              setSelectedId(null);
              reset(buildNewInstanceFormValues(instances, profiles));
            }}
          >
            New Instance
          </Button>
        </div>
        <div className="sidebar-list">
          {instances.map((instance) => (
            <button
              key={instance.id}
              type="button"
              className={`list-item ${instance.id === selectedId && !isCreating ? "active" : ""}`}
              onClick={() => {
                setIsCreating(false);
                setSelectedId(instance.id);
                reset(instanceToFormValues(instance));
              }}
            >
              <strong>{instance.label}</strong>
              <span>
                {instance.bind_host}:{instance.port}
              </span>
            </button>
          ))}
        </div>
      </aside>

      <article className="editor-card">
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="editor-header">
            <div>
              <p className="eyebrow">{isCreating ? "Create" : "Edit"}</p>
              <h3>{isCreating ? "New Instance Draft" : currentLabel || activeInstance?.label || "Instance"}</h3>
            </div>
            <div className="editor-actions">
              {!isCreating && activeInstance ? (
                <Button
                  size="sm"
                  type="button"
                  variant="destructive"
                  onClick={async () => {
                    if (!window.confirm(`Delete instance ${activeInstance.id} from the draft?`)) {
                      return;
                    }
                    await onDeleteInstance(activeInstance.id);
                    setSelectedId(null);
                  }}
                >
                  Delete
                </Button>
              ) : null}
              <Button disabled={busy || (!isCreating && !isDirty)} type="submit">
                {busy ? "Saving..." : isCreating ? "Create Draft Instance" : "Save Draft Instance"}
              </Button>
            </div>
          </div>

          <div className="form-grid">
            <label>
              <span>Instance ID</span>
              <Input
                aria-invalid={errors.id ? true : undefined}
                readOnly={!isCreating}
                {...register("id", {
                  required: "Instance ID is required.",
                })}
              />
              <FieldError message={errors.id?.message} />
            </label>
            <label>
              <span>Label</span>
              <Input
                aria-invalid={errors.label ? true : undefined}
                {...register("label", {
                  required: "Label is required.",
                })}
              />
              <FieldError message={errors.label?.message} />
            </label>
            <label>
              <span>Profile</span>
              <Controller
                control={control}
                name="profile_id"
                rules={{ required: "Profile is required." }}
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger aria-invalid={errors.profile_id ? true : undefined} className="w-full">
                      <SelectValue placeholder="Select a profile" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        {profiles.map((profile) => (
                          <SelectItem key={profile.id} value={profile.id}>
                            {profile.label}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                )}
              />
              <FieldError message={errors.profile_id?.message} />
            </label>
            <label>
              <span>Port</span>
              <Input
                aria-invalid={errors.port ? true : undefined}
                type="number"
                {...register("port", {
                  valueAsNumber: true,
                  required: "Port is required.",
                  validate: (value) =>
                    Number.isInteger(value) || "Port must be an integer between 1 and 65535.",
                  min: {
                    value: 1,
                    message: "Port must be between 1 and 65535.",
                  },
                  max: {
                    value: 65535,
                    message: "Port must be between 1 and 65535.",
                  },
                })}
              />
              <FieldError message={errors.port?.message} />
            </label>
            <label>
              <span>Bind Host</span>
              <Input
                aria-invalid={errors.bind_host ? true : undefined}
                {...register("bind_host", {
                  required: "Bind host is required.",
                })}
              />
              <FieldError message={errors.bind_host?.message} />
            </label>
            <label className="full-width">
              <span>Prompt Config Path</span>
              <Input
                aria-invalid={errors.prompt_config_path ? true : undefined}
                {...register("prompt_config_path", {
                  required: "Prompt config path is required.",
                })}
              />
              <FieldError message={errors.prompt_config_path?.message} />
            </label>
            <label className="checkbox-field">
              <input type="checkbox" {...register("enabled")} />
              <span>Enabled</span>
            </label>
          </div>

          <details className="advanced-card">
            <summary>Advanced</summary>
            <div className="form-grid advanced-grid">
              <label>
                <span>Runtime</span>
                <Input readOnly {...register("runtime")} />
              </label>
              <label>
                <span>State Group</span>
                <Input
                  aria-invalid={errors.state_group ? true : undefined}
                  {...register("state_group", {
                    required: "State group is required.",
                  })}
                />
                <FieldError message={errors.state_group?.message} />
              </label>
              <label>
                <span>Compose Service</span>
                <Input {...register("compose_service_name")} />
              </label>
              <label>
                <span>Container Name</span>
                <Input {...register("container_name")} />
              </label>
              <label>
                <span>Env Prefix</span>
                <Input {...register("env_prefix")} />
              </label>
              <label>
                <span>Healthcheck Path</span>
                <Input
                  aria-invalid={errors.healthcheck_path ? true : undefined}
                  {...register("healthcheck_path", {
                    required: "Healthcheck path is required.",
                  })}
                />
                <FieldError message={errors.healthcheck_path?.message} />
              </label>
              <label className="full-width">
                <span>Mutable Fields</span>
                <Input {...register("mutable_fields")} />
              </label>
              <label>
                <span>UI Order</span>
                <Input
                  aria-invalid={errors.ui_order ? true : undefined}
                  type="number"
                  {...register("ui_order", {
                    valueAsNumber: true,
                    min: {
                      value: 0,
                      message: "UI Order must be 0 or greater.",
                    },
                  })}
                />
                <FieldError message={errors.ui_order?.message} />
              </label>
            </div>
          </details>
        </form>
      </article>
    </section>
  );
}
